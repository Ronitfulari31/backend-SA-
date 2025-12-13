"""
Location Extraction Service
Extracts locations (city, state, country) from text using spaCy NER
"""

import logging
import time
from typing import Dict, List
import spacy

logger = logging.getLogger(__name__)


class LocationExtractionService:
    """Service for location extraction from text"""
    
    def __init__(self):
        self.nlp = None
        self._load_spacy_model()
    
    def _load_spacy_model(self):
        """Load spaCy model for NER"""
        try:
            logger.info("Loading spaCy model...")
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            logger.info("Run: python -m spacy download en_core_web_sm")
    
    def extract_entities(self, text: str) -> List[Dict]:
        """
        Extract all named entities from text
        
        Args:
            text: Input text
            
        Returns:
            List of entities with text and label
        """
        if self.nlp is None:
            logger.error("spaCy model not loaded")
            return []
        
        try:
            doc = self.nlp(text)
            entities = [
                {
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char
                }
                for ent in doc.ents
            ]
            
            return entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    def extract_locations(self, text: str) -> Dict:
        """
        Extract location information from text
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with:
                - locations: List of structured location dictionaries
                - extraction_time: Time taken
        """
        start_time = time.time()
        
        try:
            if not text or len(text.strip()) == 0:
                return {
                    'locations': [],
                    'extraction_time': 0.0
                }
            
            if self.nlp is None:
                logger.error("spaCy model not available")
                return {
                    'locations': [],
                    'extraction_time': 0.0,
                    'error': 'spaCy model not loaded'
                }
            
            # Extract all entities
            doc = self.nlp(text)
            
            # Filter for location entities (GPE = Geo-Political Entity, LOC = Location)
            location_entities = []
            
            for ent in doc.ents:
                if ent.label_ in ['GPE', 'LOC']:
                    location_entities.append({
                        'entity_text': ent.text,
                        'entity_type': ent.label_,
                        'location_type': self._classify_location_type(ent.text)
                    })
            
            # Structure locations
            structured_locations = self._structure_locations(location_entities)
            
            extraction_time = time.time() - start_time
            
            logger.info(f"Extracted {len(structured_locations)} locations in {extraction_time:.3f}s")
            
            return {
                'locations': structured_locations,
                'extraction_time': round(extraction_time, 3)
            }
            
        except Exception as e:
            extraction_time = time.time() - start_time
            logger.error(f"Location extraction failed: {e}")
            
            return {
                'locations': [],
                'extraction_time': round(extraction_time, 3),
                'error': str(e)
            }
    
    def _classify_location_type(self, location_text: str) -> str:
        """
        Classify location as city, state, or country (simple heuristic)
        
        Args:
            location_text: Location name
            
        Returns:
            'city', 'state', 'country', or 'unknown'
        """
        # Common country names (simplified)
        countries = {
            'india', 'usa', 'united states', 'china', 'japan', 'uk', 'united kingdom',
            'france', 'germany', 'spain', 'italy', 'russia', 'brazil', 'mexico',
            'australia', 'canada', 'pakistan', 'bangladesh', 'nepal', 'sri lanka'
        }
        
        # Common Indian states (for disaster context)
        indian_states = {
            'maharashtra', 'karnataka', 'tamil nadu', 'kerala', 'gujarat', 
            'rajasthan', 'punjab', 'haryana', 'uttar pradesh', 'bihar',
            'west bengal', 'odisha', 'assam', 'uttarakhand', 'himachal pradesh'
        }
        
        location_lower = location_text.lower()
        
        if location_lower in countries:
            return 'country'
        elif location_lower in indian_states:
            return 'state'
        else:
            # Default to city for GPE entities
            return 'city'
    
    def _structure_locations(self, location_entities: List[Dict]) -> List[Dict]:
        """
        Structure location entities into city/state/country format
        
        Args:
            location_entities: List of location entities
            
        Returns:
            List of structured location dictionaries
        """
        structured = []
        
        for entity in location_entities:
            loc = {
                'entity_text': entity['entity_text'],
                'location_type': entity['location_type']
            }
            
            # Add to appropriate field
            if entity['location_type'] == 'city':
                loc['city'] = entity['entity_text']
                loc['state'] = None
                loc['country'] = None
            elif entity['location_type'] == 'state':
                loc['city'] = None
                loc['state'] = entity['entity_text']
                loc['country'] = None
            elif entity['location_type'] == 'country':
                loc['city'] = None
                loc['state'] = None
                loc['country'] = entity['entity_text']
            else:
                # Default to city
                loc['city'] = entity['entity_text']
                loc['state'] = None
                loc['country'] = None
            
            structured.append(loc)
        
        return structured
    
    def get_location_summary(self, locations: List[Dict]) -> Dict:
        """
        Get summary of extracted locations
        
        Args:
            locations: List of location dictionaries
            
        Returns:
            Summary with counts by type
        """
        summary = {
            'total_locations': len(locations),
            'cities': [],
            'states': [],
            'countries': []
        }
        
        for loc in locations:
            if loc.get('city'):
                summary['cities'].append(loc['city'])
            if loc.get('state'):
                summary['states'].append(loc['state'])
            if loc.get('country'):
                summary['countries'].append(loc['country'])
        
        # Remove duplicates
        summary['cities'] = list(set(summary['cities']))
        summary['states'] = list(set(summary['states']))
        summary['countries'] = list(set(summary['countries']))
        
        return summary


# Singleton instance
location_extraction_service = LocationExtractionService()
