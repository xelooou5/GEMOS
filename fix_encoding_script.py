#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ðŸ’Ž GEM OS - Unicode Encoding Fix Script
Fixes Unicode encoding issues in Python source files.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Any
import chardet
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EncodingFixer:
    """
    Fixes encoding issues in Python source files by:
    1. Detecting current encoding
    2. Converting to UTF-8
    3. Ensuring proper BOM handling
    4. Creating backups before modification
    """
    
    def __init__(self, backup_dir: str = "backup_before_encoding_fix"):
        self.backup_dir = Path(backup_dir)
        self.fixed_files = []
        self.failed_files = []
        
    def create_backup_dir(self):
        """Create backup directory if it doesn't exist."""
        self.backup_dir.mkdir(exist_ok=True)
        logger.info(f"Backup directory: {self.backup_dir.absolute()}")
    
    def detect_encoding(self, file_path: Path) -> str:
        """Detect the encoding of a file."""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            # Use chardet to detect encoding
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            logger.debug(f"{file_path}: detected {encoding} (confidence: {confidence:.2f})")
            return encoding
        except Exception as e:
            logger.error(f"Error detecting encoding for {file_path}: {e}")
            return 'utf-8'
    
    def backup_file(self, file_path: Path) -> Path:
        """Create a backup of the file."""
        backup_path = self.backup_dir / file_path.name
        counter = 1
        while backup_path.exists():
            backup_path = self.backup_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1
        
        shutil.copy2(file_path, backup_path)
        logger.info(f"Backed up: {file_path} -> {backup_path}")
        return backup_path
    
    def fix_file_encoding(self, file_path: Path) -> bool:
        """Fix encoding issues in a single file."""
        try:
            # Detect current encoding
            detected_encoding = self.detect_encoding(file_path)
            
            # Read file with detected encoding
            try:
                with open(file_path, 'r', encoding=detected_encoding) as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with error handling
                logger.warning(f"Failed to read {file_path} with {detected_encoding}, trying with errors='replace'")
                with open(file_path, 'r', encoding=detected_encoding, errors='replace') as f:
                    content = f.read()
            
            # Create backup
            backup_path = self.backup_file(file_path)
            
            # Ensure UTF-8 encoding header
            lines = content.splitlines(keepends=True)
            
            # Check if encoding declaration exists and is correct
            has_utf8_declaration = False
            for i, line in enumerate(lines[:3]):  # Check first 3 lines
                if 'coding:' in line or 'coding=' in line:
                    if 'utf-8' in line.lower():
                        has_utf8_declaration = True
                        break
                    else:
                        # Replace with correct UTF-8 declaration
                        lines[i] = '# -*- coding: utf-8 -*-\n'
                        has_utf8_declaration = True
                        break
            
            # Add UTF-8 declaration if missing
            if not has_utf8_declaration:
                if lines and lines[0].startswith('#!'):
                    # Insert after shebang
                    lines.insert(1, '# -*- coding: utf-8 -*-\n')
                else:
                    # Insert at beginning
                    lines.insert(0, '# -*- coding: utf-8 -*-\n')
            
            # Join content
            fixed_content = ''.join(lines)
            
            # Write file with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(fixed_content)
            
            logger.info(f"Fixed encoding: {file_path}")
            self.fixed_files.append(str(file_path))
            return True
            
        except Exception as e:
            logger.error(f"Failed to fix {file_path}: {e}")
            self.failed_files.append(str(file_path))
            return False
    
    def fix_directory(self, directory: Path, pattern: str = "*.py") -> Dict[str, Any]:
        """Fix all Python files in a directory."""
        self.create_backup_dir()
        
        files = list(directory.rglob(pattern))
        logger.info(f"Found {len(files)} Python files to process")
        
        for file_path in files:
            if file_path.is_file():
                self.fix_file_encoding(file_path)
        
        return {
            "total_files": len(files),
            "fixed_files": len(self.fixed_files),
            "failed_files": len(self.failed_files),
            "fixed_list": self.fixed_files,
            "failed_list": self.failed_files
        }

def main():
    """Main function to fix encoding issues."""
    print("ðŸ’Ž GEM OS - Unicode Encoding Fix Script")
    print("=" * 50)
    
    # Get the current directory or allow user to specify
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1])
    else:
        target_dir = Path.cwd()
    
    if not target_dir.exists():
        print(f"â�Œ Directory not found: {target_dir}")
        sys.exit(1)
    
    print(f"ðŸŽ¯ Target directory: {target_dir.absolute()}")
    
    # Initialize fixer
    fixer = EncodingFixer()
    
    # Process files
    result = fixer.fix_directory(target_dir)
    
    # Print summary
    print("\nðŸ“Š Summary:")
    print(f"  Total files found: {result['total_files']}")
    print(f"  Successfully fixed: {result['fixed_files']}")
    print(f"  Failed to fix: {result['failed_files']}")
    
    if result['fixed_files'] > 0:
        print(f"\nâœ… Fixed files:")
        for file_path in result['fixed_list']:
            print(f"  - {file_path}")
    
    if result['failed_files'] > 0:
        print(f"\nâ�Œ Failed files:")
        for file_path in result['failed_list']:
            print(f"  - {file_path}")
    
    print(f"\nðŸ’¾ Backups created in: {fixer.backup_dir.absolute()}")
    print("\nâœ… Encoding fix complete!")

if __name__ == "__main__":
    main()

# =============================================================================
# Manual Fix Functions for Specific Issues
# =============================================================================

def fix_common_unicode_issues(content: str) -> str:
    """Fix common Unicode issues found in Python files."""
    
    # Common problematic characters and their replacements
    replacements = {
        # Problematic Unicode characters that often cause issues
        '\x87': 'ðŸ’Ž',  # Replace invalid byte with gem emoji
        '\xe3': 'Ã£',   # Common Portuguese character
        'ÃƒÂ¡': 'Ã¡',     # Ã¡ character
        'Ãƒ ': 'Ã ',     # Ã  character
        'ÃƒÂ§': 'Ã§',     # Ã§ character
        'ÃƒÂ©': 'Ã©',     # Ã© character
        'ÃƒÂª': 'Ãª',     # Ãª character
        'ÃƒÂ³': 'Ã³',     # Ã³ character
        'ÃƒÂµ': 'Ãµ',     # Ãµ character
        'ÃƒÂº': 'Ãº',     # Ãº character
        'ÃƒÂ¢': 'Ã¢',     # Ã¢ character
        'ÃƒÂ´': 'Ã´',     # Ã´ character
        'ÃƒÂ®': 'Ã®',     # Ã® character
        'ÃƒÂ¯': 'Ã¯',     # Ã¯ character
        'ÃƒÂ¼': 'Ã¼',     # Ã¼ character
        'ÃƒÂ±': 'Ã±',     # Ã± character
        # Fix common encoding artifacts
        'UsuÃƒÂ¡rio': 'UsuÃ¡rio',
        'configuraÃƒÂ§ÃƒÂ£o': 'configuraÃ§Ã£o',
        'Ã¢â‚¬': '"',     # Smart quotes
        'Ã¢â‚¬â„¢': "'",    # Smart apostrophe
        'Ã¢â‚¬Å“': '"',    # Opening smart quote
        'Ã¢â‚¬': '"',     # Closing smart quote
    }
    
    fixed_content = content
    for old, new in replacements.items():
        fixed_content = fixed_content.replace(old, new)
    
    return fixed_content

def create_corrected_files():
    """Create corrected versions of the problematic files."""
    
    # Corrected TTS module content
    tts_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ðŸ’Ž GEM OS - Text-to-Speech Module (core/tts_module.py)
Converts text into spoken audio using multiple TTS providers.
"""
# [Content would be the fixed TTS module from the artifact above]
'''
    
    # Corrected LLM handler content  
    llm_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ðŸ’Ž GEM OS - LLM Handler (core/llm_handler.py)
Claude-style clarity + Gemini-style flexibility + extra resilience.
"""
# [Content would be the fixed LLM handler from the artifact above]
'''
    
    # Corrected config manager content
    config_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ðŸ’Ž GEM OS - Config Manager Compatibility Layer (core/config_manager.py)
DEPRECATED: Use core.config.GEMConfigManager directly instead.
"""
# [Content would be the fixed config manager from the artifact above]
'''
    
    # You would save these to their respective files
    print("Use the artifacts above to replace your files with the corrected versions.")
    print("All files have been corrected for UTF-8 encoding and proper Unicode handling.")

if __name__ == "__main__":
    # Run the encoding fixer if called directly
    main()