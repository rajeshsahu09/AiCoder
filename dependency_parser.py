# android_code_ai/dependency_parser.py
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

class AndroidDependencyParser:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.dependencies = {
            'gradle': [],
            'manifest': [],
            'compose': False,
            'libraries': set(),
            'di_frameworks': set()
        }
    
    def parse_project(self) -> Dict:
        self._parse_gradle_files()
        self._parse_manifest()
        self._check_compose()
        return self.dependencies
    
    def _parse_gradle_files(self):
        """Parse build.gradle files for dependencies"""
        build_gradle_files = list(Path(self.project_root).rglob('build.gradle')) + \
                           list(Path(self.project_root).rglob('build.gradle.kts'))
        
        for gradle_file in build_gradle_files:
            try:
                with open(gradle_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Find dependencies
                    dep_pattern = r"(implementation|api|compile|kapt|ksp)\s*\(?\s*['\"]([^:'\"]+:[^:'\"]+)['\"]"
                    matches = re.finditer(dep_pattern, content)
                    for match in matches:
                        self.dependencies['libraries'].add(match.group(2))
                    
                    # Check for Android plugins
                    if 'com.android.application' in content or 'com.android.library' in content:
                        self.dependencies['gradle'].append('android_plugin')
                    
                    # Check for Kotlin plugins
                    if 'org.jetbrains.kotlin.android' in content:
                        self.dependencies['gradle'].append('kotlin_plugin')
                    
                    # Check for DI frameworks
                    self._detect_di_frameworks(content)
            except Exception as e:
                pass
    
    def _detect_di_frameworks(self, content: str):
        """Detect DI frameworks in Gradle files"""
        di_libraries = {
            'dagger': ['com.google.dagger:dagger', 'com.google.dagger:hilt-android'],
            'hilt': ['com.google.dagger:hilt-android', 'com.google.dagger.hilt.android'],
            'koin': ['io.insert-koin:koin-android', 'io.insert-koin:koin-core']
        }
        
        for framework, libs in di_libraries.items():
            for lib in libs:
                if lib in content:
                    self.dependencies['di_frameworks'].add(framework)
    
    def _parse_manifest(self):
        """Parse AndroidManifest.xml for permissions and components"""
        manifest_path = Path(self.project_root) / 'app' / 'src' / 'main' / 'AndroidManifest.xml'
        if not manifest_path.exists():
            return
            
        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()
            
            # Parse uses-permission
            for perm in root.findall('.//uses-permission'):
                android_name = perm.get('{http://schemas.android.com/apk/res/android}name')
                if android_name:
                    self.dependencies['manifest'].append(android_name)
            
            # Parse application attributes
            application = root.find('application')
            if application is not None:
                for attr in application.attrib:
                    if 'theme' in attr or 'name' in attr:
                        self.dependencies['manifest'].append(f"{attr}:{application.attrib[attr]}")
        except:
            pass
    
    def _check_compose(self):
        """Check if Compose is used in the project"""
        # Check for Compose dependencies
        compose_deps = {
            'androidx.compose.compiler',
            'androidx.compose.runtime',
            'androidx.compose.ui'
        }
        
        if any(dep in self.dependencies['libraries'] for dep in compose_deps):
            self.dependencies['compose'] = True
        
        # Also check for Compose in Kotlin files
        compose_files = list(Path(self.project_root).rglob('*.kt'))
        for kt_file in compose_files[:10]:  # Check first 10 files
            try:
                with open(kt_file, 'r', encoding='utf-8') as f:
                    if '@Composable' in f.read():
                        self.dependencies['compose'] = True
                        break
            except:
                continue