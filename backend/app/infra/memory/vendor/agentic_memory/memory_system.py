import keyword
from typing import List, Dict, Optional, Any, Tuple
import uuid
from datetime import datetime
from .llm_controller import LLMController
from .cloud_retriever import CloudRetriever
import json
import logging
from rank_bm25 import BM25Okapi
import os
from abc import ABC, abstractmethod
from transformers import AutoModel, AutoTokenizer
from nltk.tokenize import word_tokenize
import pickle
from pathlib import Path
from litellm import completion
import time

logger = logging.getLogger(__name__)

from .models import MemoryNote
from .prompts import EVOLUTION_SYSTEM_PROMPT, CONTENT_ANALYSIS_PROMPT
from .schemas import CONTENT_ANALYSIS_SCHEMA, MEMORY_EVOLUTION_SCHEMA

class AgenticMemorySystem:
    """
    Core memory system managing memory notes and their evolution.
    """
    
    def __init__(self, 
                 retriever: CloudRetriever,
                 llm_controller: LLMController,
                 evo_threshold: int = 100):
        """
        Initialize the memory system with injected dependencies.
        """
        self.memories = {}
        self.retriever = retriever
        self.llm_controller = llm_controller
        self.evo_cnt = 0
        self.evo_threshold = evo_threshold
        self._evolution_system_prompt = EVOLUTION_SYSTEM_PROMPT
        
    def analyze_content(self, content: str) -> Dict:            
        """
        Analyze content using LLM to extract semantic metadata.
        """
        prompt = CONTENT_ANALYSIS_PROMPT.format(content=content)
        try:
            response = self.llm_controller.get_completion(
                prompt, 
                response_format=CONTENT_ANALYSIS_SCHEMA
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return {"keywords": [], "context": "General", "tags": []}

    def _build_metadata(self, note: MemoryNote) -> dict:
        """统一构建 memory metadata dict，消除内联重复。"""
        return {
            "id": note.id,
            "content": note.content,
            "keywords": note.keywords,
            "links": note.links,
            "retrieval_count": note.retrieval_count,
            "timestamp": note.timestamp,
            "last_accessed": note.last_accessed,
            "context": note.context,
            "evolution_history": note.evolution_history,
            "category": note.category,
            "tags": note.tags
        }

    async def add_note(self, content: str, time: str = None, **kwargs) -> str:
        """Add a new memory note"""
        if time is not None:
            kwargs['timestamp'] = time
        note = MemoryNote(content=content, **kwargs)

        evo_label, note = await self.process_memory(note)
        self.memories[note.id] = note

        await self.retriever.add_document(note.content, self._build_metadata(note), note.id)

        if evo_label:
            self.evo_cnt += 1
            if self.evo_cnt % self.evo_threshold == 0:
                await self.consolidate_memories()
        return note.id

    async def consolidate_memories(self):
        """Consolidate memories by re-indexing all documents"""
        for memory in self.memories.values():
            await self.retriever.add_document(memory.content, self._build_metadata(memory), memory.id)
    
    async def find_related_memories(self, query: str, k: int = 5) -> Tuple[str, List[int]]:
        """Find related memories using CloudRetriever retrieval"""
        if not self.memories:
            return "", []

        try:
            results = await self.retriever.search(query, k)

            memory_str = ""
            indices = []

            if 'ids' in results and results['ids'] and len(results['ids']) > 0 and len(results['ids'][0]) > 0:
                for i, doc_id in enumerate(results['ids'][0]):
                    if i < len(results['metadatas'][0]):
                        metadata = results['metadatas'][0][i]
                        memory_str += f"memory index:{i}\ttalk start time:{metadata.get('timestamp', '')}\tmemory content: {metadata.get('content', '')}\tmemory context: {metadata.get('context', '')}\tmemory keywords: {str(metadata.get('keywords', []))}\tmemory tags: {str(metadata.get('tags', []))}\n"
                        indices.append(i)

            return memory_str, indices
        except Exception as e:
            logger.error(f"Error in find_related_memories: {str(e)}")
            return "", []

    async def find_related_memories_raw(self, query: str, k: int = 5) -> str:
        """Find related memories using CloudRetriever retrieval in raw format"""
        if not self.memories:
            return ""

        results = await self.retriever.search(query, k)

        memory_str = ""

        if 'ids' in results and results['ids'] and len(results['ids']) > 0:
            for i, doc_id in enumerate(results['ids'][0][:k]):
                if i < len(results['metadatas'][0]):
                    metadata = results['metadatas'][0][i]

                    memory_str += f"talk start time:{metadata.get('timestamp', '')}\tmemory content: {metadata.get('content', '')}\tmemory context: {metadata.get('context', '')}\tmemory keywords: {str(metadata.get('keywords', []))}\tmemory tags: {str(metadata.get('tags', []))}\n"

                    links = metadata.get('links', [])
                    j = 0
                    for link_id in links:
                        if link_id in self.memories and j < k:
                            neighbor = self.memories[link_id]
                            memory_str += f"talk start time:{neighbor.timestamp}\tmemory content: {neighbor.content}\tmemory context: {neighbor.context}\tmemory keywords: {str(neighbor.keywords)}\tmemory tags: {str(neighbor.tags)}\n"
                            j += 1

        return memory_str

    def read(self, memory_id: str) -> Optional[MemoryNote]:
        """Retrieve a memory note by its ID.
        
        Args:
            memory_id (str): ID of the memory to retrieve
            
        Returns:
            MemoryNote if found, None otherwise
        """
        return self.memories.get(memory_id)
    
    async def update(self, memory_id: str, **kwargs) -> bool:
        """Update a memory note.

        Args:
            memory_id: ID of memory to update
            **kwargs: Fields to update

        Returns:
            bool: True if update successful
        """
        if memory_id not in self.memories:
            return False

        note = self.memories[memory_id]

        for key, value in kwargs.items():
            if hasattr(note, key):
                setattr(note, key, value)

        metadata = self._build_metadata(note)

        await self.retriever.delete_document(memory_id)
        await self.retriever.add_document(document=note.content, metadata=metadata, doc_id=memory_id)

        return True

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory note by its ID.

        Args:
            memory_id (str): ID of the memory to delete

        Returns:
            bool: True if memory was deleted, False if not found
        """
        if memory_id in self.memories:
            await self.retriever.delete_document(memory_id)
            del self.memories[memory_id]
            return True
        return False

    async def _search_raw(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Internal search method that returns raw results from CloudRetriever.

        This is used internally by the memory evolution system to find
        related memories for potential evolution.
        
        Args:
            query (str): The search query text
            k (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: Raw search results from CloudRetriever
        """
        results = await self.retriever.search(query, k)
        return [{'id': doc_id, 'score': score} 
                for doc_id, score in zip(results['ids'][0], results['distances'][0])]
                
    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for memories using CloudRetriever retrieval."""
        search_results = await self.retriever.search(query, k)
        memories = []

        for i, doc_id in enumerate(search_results['ids'][0]):
            memory = self.memories.get(doc_id)
            if memory:
                memories.append({
                    'id': doc_id,
                    'content': memory.content,
                    'context': memory.context,
                    'keywords': memory.keywords,
                    'score': search_results['distances'][0][i]
                })

        return memories[:k]
    
    async def _search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Legacy hybrid search (now single-source via CloudRetriever)."""
        results = await self.retriever.search(query, k)
        memories = []

        for i, doc_id in enumerate(results['ids'][0]):
            memory = self.memories.get(doc_id)
            if memory:
                memories.append({
                    'id': doc_id,
                    'content': memory.content,
                    'context': memory.context,
                    'keywords': memory.keywords,
                    'score': results['distances'][0][i]
                })

        return memories[:k]

    async def search_agentic(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for memories using CloudRetriever retrieval."""
        if not self.memories:
            return []

        try:
            results = await self.retriever.search(query, k)

            memories = []
            seen_ids = set()

            if ('ids' not in results or not results['ids'] or
                len(results['ids']) == 0 or len(results['ids'][0]) == 0):
                return []

            for i, doc_id in enumerate(results['ids'][0][:k]):
                if doc_id in seen_ids:
                    continue
                    
                if i < len(results['metadatas'][0]):
                    metadata = results['metadatas'][0][i]
                    
                    # Create result dictionary with all metadata fields
                    memory_dict = {
                        'id': doc_id,
                        'content': metadata.get('content', ''),
                        'context': metadata.get('context', ''),
                        'keywords': metadata.get('keywords', []),
                        'tags': metadata.get('tags', []),
                        'timestamp': metadata.get('timestamp', ''),
                        'category': metadata.get('category', 'Uncategorized'),
                        'is_neighbor': False
                    }
                    
                    # Add score if available
                    if 'distances' in results and len(results['distances']) > 0 and i < len(results['distances'][0]):
                        memory_dict['score'] = results['distances'][0][i]
                        
                    memories.append(memory_dict)
                    seen_ids.add(doc_id)
            
            # Add linked memories (neighbors)
            neighbor_count = 0
            for memory in list(memories):  # Use a copy to avoid modification during iteration
                if neighbor_count >= k:
                    break
                    
                # Get links from metadata
                links = memory.get('links', [])
                if not links and 'id' in memory:
                    # Try to get links from memory object
                    mem_obj = self.memories.get(memory['id'])
                    if mem_obj:
                        links = mem_obj.links
                        
                for link_id in links:
                    if link_id not in seen_ids and neighbor_count < k:
                        neighbor = self.memories.get(link_id)
                        if neighbor:
                            memories.append({
                                'id': link_id,
                                'content': neighbor.content,
                                'context': neighbor.context,
                                'keywords': neighbor.keywords,
                                'tags': neighbor.tags,
                                'timestamp': neighbor.timestamp,
                                'category': neighbor.category,
                                'is_neighbor': True
                            })
                            seen_ids.add(link_id)
                            neighbor_count += 1
            
            return memories[:k]
        except Exception as e:
            logger.error(f"Error in search_agentic: {str(e)}")
            return []

    async def process_memory(self, note: MemoryNote) -> Tuple[bool, MemoryNote]:
        """Process a memory note and determine if it should evolve."""
        if not self.memories:
            return False, note

        try:
            neighbors_text, indices = await self.find_related_memories(note.content, k=5)
            if not neighbors_text or not indices:
                return False, note
                
            prompt = self._evolution_system_prompt.format(
                content=note.content,
                context=note.context,
                keywords=note.keywords,
                nearest_neighbors_memories=neighbors_text,
                neighbor_number=len(indices)
            )
            
            try:
                response = self.llm_controller.get_completion(
                    prompt,
                    response_format=MEMORY_EVOLUTION_SCHEMA
                )
                
                response_json = json.loads(response)
                should_evolve = response_json["should_evolve"]
                
                if should_evolve:
                    actions = response_json["actions"]
                    suggest_connections = response_json["suggested_connections"]
                    
                    # Apply logical connections
                    for conn in suggest_connections:
                        note.links.append({
                            "id": conn["id"],
                            "type": conn["type"],
                            "reason": conn["reason"]
                        })

                    for action in actions:
                        if action in ["strengthen", "contradict"]:
                            note.tags = response_json["tags_to_update"]
                        elif action == "update_neighbor":
                            new_context_neighborhood = response_json["new_context_neighborhood"]
                            new_tags_neighborhood = response_json["new_tags_neighborhood"]
                            noteslist = list(self.memories.values())
                            notes_id = list(self.memories.keys())
                            
                            for i in range(min(len(indices), len(new_tags_neighborhood))):
                                if i >= len(indices):
                                    continue
                                    
                                tag = new_tags_neighborhood[i]
                                if i < len(new_context_neighborhood):
                                    context = new_context_neighborhood[i]
                                else:
                                    if i < len(noteslist):
                                        context = noteslist[i].context
                                    else:
                                        continue
                                        
                                if i < len(indices):
                                    memorytmp_idx = indices[i]
                                    if memorytmp_idx < len(noteslist):
                                        notetmp = noteslist[memorytmp_idx]
                                        notetmp.tags = tag
                                        notetmp.context = context
                                        if memorytmp_idx < len(notes_id):
                                            self.memories[notes_id[memorytmp_idx]] = notetmp
                                
                return should_evolve, note
                
            except (json.JSONDecodeError, KeyError, Exception) as e:
                logger.error(f"Error in memory evolution: {str(e)}")
                return False, note
                
        except Exception as e:
            logger.error(f"Error in process_memory: {str(e)}")
            return False, note
