#!/usr/bin/env python3
"""
Validation script to detect three critical XSD repository issues:
- Issue #331: Duplicate XSD files with same targetNamespace
- Issue #332: Version numbers embedded in filenames
- Issue #333: Unencoded space characters in schemaLocation URIs

Usage: python3 validate-xsd-issues.py
"""

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class XSDValidator:
    def __init__(self, root_dir: Path = Path('.')):
        self.root_dir = root_dir
        self.xsd_files = list(root_dir.glob('**/*.xsd'))
        self.namespaces = {
            'xs': 'http://www.w3.org/2001/XMLSchema',
            'xsd': 'http://www.w3.org/2001/XMLSchema'
        }

    def compute_file_hash(self, filepath: Path) -> str:
        """Compute SHA256 hash of file contents."""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_target_namespace(self, filepath: Path) -> str:
        """Extract targetNamespace from XSD file."""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            return root.get('targetNamespace', '')
        except Exception:
            return ''

    def check_duplicates(self) -> Dict[str, List[Path]]:
        """Issue #331: Find duplicate XSD files."""
        hash_to_files = defaultdict(list)

        for xsd_file in self.xsd_files:
            file_hash = self.compute_file_hash(xsd_file)
            hash_to_files[file_hash].append(xsd_file)

        # Return only duplicates (hash appears more than once)
        return {h: files for h, files in hash_to_files.items() if len(files) > 1}

    def check_version_in_filenames(self) -> List[Tuple[Path, str]]:
        """Issue #332: Find files with version numbers in names."""
        version_pattern = re.compile(r'[_\-]v?\d+\.\d+', re.IGNORECASE)
        versioned_files = []

        for xsd_file in self.xsd_files:
            match = version_pattern.search(xsd_file.name)
            if match:
                versioned_files.append((xsd_file, match.group()))

        return versioned_files

    def check_unencoded_spaces(self) -> List[Tuple[Path, int, str]]:
        """Issue #333: Find schemaLocation attributes with unencoded spaces."""
        violations = []
        schema_location_pattern = re.compile(
            r'schemaLocation\s*=\s*["\']([^"\']*[^%]\s[^"\']*)["\']'
        )

        for xsd_file in self.xsd_files:
            try:
                with open(xsd_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        matches = schema_location_pattern.findall(line)
                        for match in matches:
                            if ' ' in match and '%20' not in match:
                                violations.append((xsd_file, line_num, match))
            except Exception as e:
                print(f"Warning: Could not read {xsd_file}: {e}")

        return violations

    def print_report(self):
        """Generate and print validation report."""
        print("=" * 80)
        print("XSD REPOSITORY VALIDATION REPORT")
        print("=" * 80)
        print()

        # Issue #331: Duplicates
        print("ISSUE #331: Duplicate XSD Files")
        print("-" * 80)
        duplicates = self.check_duplicates()

        if duplicates:
            print(f"Found {len(duplicates)} sets of duplicate files:")
            print()

            for idx, (file_hash, files) in enumerate(duplicates.items(), 1):
                print(f"{idx}. {len(files)} identical files (hash: {file_hash[:12]}...):")

                # Get target namespace from first file
                target_ns = self.get_target_namespace(files[0])
                if target_ns:
                    print(f"   Target Namespace: {target_ns}")

                for f in files:
                    print(f"   - {f.relative_to(self.root_dir)}")
                print()
        else:
            print("✓ No duplicate files found")
            print()

        # Issue #332: Version numbers
        print("ISSUE #332: Version Numbers in Filenames")
        print("-" * 80)
        versioned = self.check_version_in_filenames()

        if versioned:
            print(f"Found {len(versioned)} files with version numbers in names:")
            print()

            for filepath, version in versioned[:10]:  # Show first 10
                print(f"  - {filepath.relative_to(self.root_dir)} (contains '{version}')")

            if len(versioned) > 10:
                print(f"  ... and {len(versioned) - 10} more")
            print()
        else:
            print("✓ No version numbers in filenames")
            print()

        # Issue #333: Unencoded spaces
        print("ISSUE #333: Unencoded Spaces in schemaLocation")
        print("-" * 80)
        space_violations = self.check_unencoded_spaces()

        if space_violations:
            print(f"Found {len(space_violations)} schemaLocation attributes with unencoded spaces:")
            print()

            for filepath, line_num, location in space_violations[:10]:  # Show first 10
                print(f"  - {filepath.relative_to(self.root_dir)}:{line_num}")
                print(f"    schemaLocation=\"{location}\"")

            if len(space_violations) > 10:
                print(f"  ... and {len(space_violations) - 10} more")
            print()
        else:
            print("✓ No unencoded spaces in schemaLocation attributes")
            print()

        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        total_issues = len(duplicates) + len(versioned) + len(space_violations)
        print(f"Total XSD files scanned: {len(self.xsd_files)}")
        print(f"Issue #331 (Duplicates): {len(duplicates)} duplicate sets found")
        print(f"Issue #332 (Versions in filenames): {len(versioned)} files")
        print(f"Issue #333 (Unencoded spaces): {len(space_violations)} violations")
        print()

        if total_issues > 0:
            print("❌ VALIDATION FAILED - Issues detected")
            return 1
        else:
            print("✓ VALIDATION PASSED - No issues detected")
            return 0


if __name__ == '__main__':
    validator = XSDValidator()
    exit_code = validator.print_report()
    exit(exit_code)
