# android_code_ai/di_analyzer.py
import re
from typing import Dict, Optional

class DIAnalyzer:
    def __init__(self):
        self.di_frameworks = {
            'dagger': {
                'annotations': ['@Inject', '@Provides', '@Binds', '@Module', '@Component'],
                'patterns': [r'Dagger[A-Z]\w*Component']
            },
            'hilt': {
                'annotations': ['@HiltAndroidApp', '@AndroidEntryPoint', '@HiltViewModel'],
                'patterns': [r'Hilt[A-Z]\w*']
            },
            'koin': {
                'annotations': [],
                'patterns': [r'startKoin', r'module\s*{', r'single\s*{', r'factory\s*{']
            }
        }
        self.detected_frameworks = set()
    
    def analyze_file(self, file_path: str, content: str) -> Optional[Dict]:
        """Analyze a file for DI framework usage"""
        results = {
            'file_path': file_path,
            'framework': None,
            'components': [],
            'modules': [],
            'providers': [],
            'injection_points': []
        }
        
        # Detect DI framework
        framework = self._detect_framework(content)
        if not framework:
            return None
        
        results['framework'] = framework
        self.detected_frameworks.add(framework)
        
        # Framework-specific analysis
        if framework in ['dagger', 'hilt']:
            results.update(self._analyze_dagger_hilt(content))
        elif framework == 'koin':
            results.update(self._analyze_koin(content))
        
        return results
    
    def _detect_framework(self, content: str) -> Optional[str]:
        """Detect which DI framework is being used"""
        for framework, config in self.di_frameworks.items():
            # Check for annotations
            for annotation in config['annotations']:
                if annotation in content:
                    return framework
            
            # Check for patterns
            for pattern in config['patterns']:
                if re.search(pattern, content):
                    return framework
        return None
    
    def _analyze_dagger_hilt(self, content: str) -> Dict:
        """Analyze Dagger/Hilt specific components"""
        analysis = {
            'components': [],
            'modules': [],
            'providers': [],
            'injection_points': []
        }
        
        # Find components
        component_matches = re.finditer(r'@Component(?:\([^)]*\))?\s+(?:interface|abstract\s+class)\s+(\w+)', content)
        analysis['components'] = [m.group(1) for m in component_matches]
        
        # Find modules
        module_matches = re.finditer(r'@Module(?:\([^)]*\))?\s+(?:class|interface|object)\s+(\w+)', content)
        analysis['modules'] = [m.group(1) for m in module_matches]
        
        # Find providers
        provider_matches = re.finditer(r'@Provides\s+(?:fun|def)\s+(\w+)', content)
        analysis['providers'] = [m.group(1) for m in provider_matches]
        
        # Find injection points
        inject_matches = re.finditer(r'@Inject\s+(?:lateinit\s+var|val|var)\s+(\w+)', content)
        analysis['injection_points'] = [m.group(1) for m in inject_matches]
        
        return analysis
    
    def _analyze_koin(self, content: str) -> Dict:
        """Analyze Koin specific components"""
        analysis = {
            'modules': [],
            'providers': []
        }
        
        # Find module declarations
        module_matches = re.finditer(r'val\s+(\w+)\s*=\s*module\s*\{', content)
        analysis['modules'] = [m.group(1) for m in module_matches]
        
        # Find provider declarations
        single_matches = re.finditer(r'single\s*\{[^}]*?\s+(\w+)\s*\(', content)
        factory_matches = re.finditer(r'factory\s*\{[^}]*?\s+(\w+)\s*\(', content)
        analysis['providers'] = [m.group(1) for m in single_matches] + [m.group(1) for m in factory_matches]
        
        return analysis
    
    def get_detected_frameworks(self) -> list:
        """Get list of detected DI frameworks in the project"""
        return list(self.detected_frameworks)