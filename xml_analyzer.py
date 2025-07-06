# android_code_ai/xml_analyzer.py
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

class XMLAnalyzer:
    MAX_CHUNK_SIZE = 2000
    MIN_CHUNK_SIZE = 500
    
    def analyze_file(self, file_path: str, content: str) -> List[Dict]:
        """Analyze XML file and extract chunks"""
        chunks = []
        
        try:
            if file_path.endswith('AndroidManifest.xml'):
                chunks.extend(self._analyze_manifest(content, file_path))
            else:
                # Assume it's a layout XML
                chunks.extend(self._analyze_layout(content, file_path))
        except ET.ParseError:
            # Fallback to regex-based analysis
            return self._chunk_with_regex(content, file_path)
        
        return chunks
    
    def _analyze_manifest(self, content: str, file_path: str) -> List[Dict]:
        """Analyze AndroidManifest.xml"""
        chunks = []
        root = ET.fromstring(content)
        
        # Chunk permissions
        permissions = []
        for perm in root.findall('.//uses-permission'):
            android_name = perm.get('{http://schemas.android.com/apk/res/android}name')
            if android_name:
                permissions.append(android_name)
        
        if permissions:
            chunks.append({
                'type': 'manifest_permissions',
                'content': '\n'.join(permissions),
                'file_path': file_path
            })
        
        # Chunk application info
        application = root.find('application')
        if application is not None:
            app_info = []
            for attr in application.attrib:
                app_info.append(f"{attr}: {application.attrib[attr]}")
            
            chunks.append({
                'type': 'manifest_application',
                'content': '\n'.join(app_info),
                'file_path': file_path
            })
        
        return chunks
    
    def _analyze_layout(self, content: str, file_path: str) -> List[Dict]:
        """Analyze layout XML file"""
        chunks = []
        root = ET.fromstring(content)
        
        # Extract top-level elements
        for child in root:
            element_xml = ET.tostring(child, encoding='unicode')
            if len(element_xml) > self.MAX_CHUNK_SIZE:
                # Split large elements
                chunks.extend(self._split_xml_element(element_xml, file_path))
            else:
                chunks.append({
                    'type': 'layout_element',
                    'content': element_xml,
                    'file_path': file_path
                })
        
        return chunks
    
    def _split_xml_element(self, element_xml: str, file_path: str) -> List[Dict]:
        """Split large XML elements into chunks"""
        chunks = []
        current_chunk = ""
        
        # Split by child elements or attributes
        lines = element_xml.split('\n')
        for line in lines:
            if len(current_chunk) + len(line) > self.MAX_CHUNK_SIZE and current_chunk:
                chunks.append({
                    'type': 'layout_element_chunk',
                    'content': current_chunk.strip(),
                    'file_path': file_path,
                })
                current_chunk = ""
            current_chunk += line + '\n'
        
        if current_chunk.strip():
            chunks.append({
                'type': 'layout_element_chunk',
                'content': current_chunk.strip(),
                'file_path': file_path,
            })
        
        return chunks
    
    def _chunk_with_regex(self, content: str, file_path: str) -> List[Dict]:
        """Fallback XML parsing with regex"""
        chunks = []
        current_chunk = ""
        
        # Split by top-level elements
        elements = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)(?:\s[^>]*)?>.*?</\1>', content, re.DOTALL)
        for element in elements:
            if len(element) > self.MAX_CHUNK_SIZE:
                # Split large elements
                chunks.extend(self._split_xml_element(element, file_path))
            else:
                chunks.append({
                    'type': 'layout_element',
                    'content': element,
                    'file_path': file_path
                })
        
        return chunks