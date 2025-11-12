"""
BioQL IR Validation and Schema Generation Utilities

This module provides validation functions and JSON schema generation
for BioQL Intermediate Representation objects.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

# Optional jsonschema import
try:
    import jsonschema
    _jsonschema_available = True
except ImportError:
    _jsonschema_available = False
    jsonschema = None

from pydantic import BaseModel, ValidationError

from .schema import BioQLProgram, BioQLResult, Molecule


class BioQLValidationError(Exception):
    """Custom exception for BioQL validation errors."""

    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)


class SchemaValidator:
    """Validates BioQL IR objects against their schemas."""

    def __init__(self):
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

    def validate_program(self, program_data: Union[Dict[str, Any], str]) -> BioQLProgram:
        """
        Validate and parse a BioQL program.

        Args:
            program_data: Program data as dict or JSON string

        Returns:
            Validated BioQLProgram instance

        Raises:
            BioQLValidationError: If validation fails
        """
        try:
            if isinstance(program_data, str):
                program_data = json.loads(program_data)

            return BioQLProgram.parse_obj(program_data)
        except ValidationError as e:
            raise BioQLValidationError(
                f"Program validation failed: {e}",
                [{"field": err["loc"], "message": err["msg"]} for err in e.errors()]
            )
        except json.JSONDecodeError as e:
            raise BioQLValidationError(f"Invalid JSON: {e}")

    def validate_result(self, result_data: Union[Dict[str, Any], str]) -> BioQLResult:
        """
        Validate and parse a BioQL result.

        Args:
            result_data: Result data as dict or JSON string

        Returns:
            Validated BioQLResult instance

        Raises:
            BioQLValidationError: If validation fails
        """
        try:
            if isinstance(result_data, str):
                result_data = json.loads(result_data)

            return BioQLResult.parse_obj(result_data)
        except ValidationError as e:
            raise BioQLValidationError(
                f"Result validation failed: {e}",
                [{"field": err["loc"], "message": err["msg"]} for err in e.errors()]
            )
        except json.JSONDecodeError as e:
            raise BioQLValidationError(f"Invalid JSON: {e}")

    def validate_molecule(self, molecule_data: Union[Dict[str, Any], str]) -> Molecule:
        """
        Validate and parse a molecule.

        Args:
            molecule_data: Molecule data as dict or JSON string

        Returns:
            Validated Molecule instance

        Raises:
            BioQLValidationError: If validation fails
        """
        try:
            if isinstance(molecule_data, str):
                molecule_data = json.loads(molecule_data)

            return Molecule.parse_obj(molecule_data)
        except ValidationError as e:
            raise BioQLValidationError(
                f"Molecule validation failed: {e}",
                [{"field": err["loc"], "message": err["msg"]} for err in e.errors()]
            )
        except json.JSONDecodeError as e:
            raise BioQLValidationError(f"Invalid JSON: {e}")

    def validate_json_schema(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> bool:
        """
        Validate data against a JSON schema.

        Args:
            data: Data to validate
            schema: JSON schema

        Returns:
            True if valid

        Raises:
            BioQLValidationError: If validation fails
        """
        try:
            jsonschema.validate(data, schema)
            return True
        except jsonschema.ValidationError as e:
            raise BioQLValidationError(
                f"Schema validation failed: {e.message}",
                [{"path": list(e.absolute_path), "message": e.message}]
            )


class SchemaGenerator:
    """Generates JSON schemas for BioQL IR objects."""

    def __init__(self, output_dir: Optional[Path] = None):
        import tempfile
        # Use temp directory if default path is not writable
        if output_dir is None:
            default_path = Path("schemas")
            try:
                default_path.mkdir(exist_ok=True)
                self.output_dir = default_path
            except (OSError, PermissionError):
                # Fallback to temp directory
                self.output_dir = Path(tempfile.gettempdir()) / "bioql_schemas"
                self.output_dir.mkdir(exist_ok=True)
        else:
            self.output_dir = output_dir
            self.output_dir.mkdir(exist_ok=True)

    def generate_program_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for BioQLProgram."""
        return BioQLProgram.schema()

    def generate_result_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for BioQLResult."""
        return BioQLResult.schema()

    def generate_molecule_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for Molecule."""
        return Molecule.schema()

    def generate_all_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Generate all schemas and save to files."""
        schemas = {
            "program": self.generate_program_schema(),
            "result": self.generate_result_schema(),
            "molecule": self.generate_molecule_schema(),
        }

        # Save schemas to files
        for name, schema in schemas.items():
            schema_file = self.output_dir / f"{name}_schema.json"
            with open(schema_file, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2)

        return schemas

    def generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI specification for BioQL IR."""
        return {
            "openapi": "3.0.3",
            "info": {
                "title": "BioQL IR API",
                "version": "1.0.0",
                "description": "BioQL Intermediate Representation API",
            },
            "components": {
                "schemas": {
                    "BioQLProgram": self.generate_program_schema(),
                    "BioQLResult": self.generate_result_schema(),
                    "Molecule": self.generate_molecule_schema(),
                }
            },
            "paths": {
                "/programs": {
                    "post": {
                        "summary": "Submit BioQL program",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/BioQLProgram"}
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Program executed successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/BioQLResult"}
                                    }
                                },
                            }
                        },
                    }
                }
            },
        }


class ComplianceValidator:
    """Validates BioQL programs for regulatory compliance."""

    def __init__(self):
        self.required_fields = [
            "id",
            "name",
            "version",
            "created_at",
            "created_by"
        ]

    def validate_21cfr_part11_compliance(self, program: BioQLProgram) -> Dict[str, Any]:
        """
        Validate program for 21 CFR Part 11 compliance.

        Args:
            program: BioQL program to validate

        Returns:
            Compliance report
        """
        report = {
            "compliant": True,
            "issues": [],
            "recommendations": []
        }

        # Check required metadata
        for field in self.required_fields:
            if not getattr(program, field, None):
                report["compliant"] = False
                report["issues"].append(f"Missing required field: {field}")

        # Check audit trail
        if not program.audit_trail:
            report["compliant"] = False
            report["issues"].append("Audit trail is empty")

        # Check for electronic signatures (placeholder)
        if not any("signature" in entry.get("action", "") for entry in program.audit_trail):
            report["recommendations"].append("Consider adding electronic signatures")

        # Check data integrity
        if not program.id:
            report["compliant"] = False
            report["issues"].append("Program must have unique identifier")

        return report

    def validate_gxp_compliance(self, program: BioQLProgram) -> Dict[str, Any]:
        """
        Validate program for GxP compliance.

        Args:
            program: BioQL program to validate

        Returns:
            Compliance report
        """
        report = {
            "compliant": True,
            "issues": [],
            "recommendations": []
        }

        # Check validation status
        if "validation_status" not in program.metadata:
            report["recommendations"].append("Add validation status to metadata")

        # Check version control
        if not program.version:
            report["compliant"] = False
            report["issues"].append("Version information required for GxP compliance")

        # Check documentation
        if not program.description:
            report["recommendations"].append("Add detailed program description")

        return report


# Create global instances for easy access
validator = SchemaValidator()
schema_generator = SchemaGenerator()
compliance_validator = ComplianceValidator()

# Export main functions
__all__ = [
    "BioQLValidationError",
    "SchemaValidator",
    "SchemaGenerator",
    "ComplianceValidator",
    "validator",
    "schema_generator",
    "compliance_validator"
]