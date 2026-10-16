"""Generate the representative two-member dossier used for visual QA."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

from mingo_assistant.services.documents.business_registration_variants import (
    TWO_MEMBER_INDIVIDUAL_TEMPLATE_RELATIVE_DIR,
)
from mingo_assistant.services.documents.two_member_individual_generator import (
    TwoMemberIndividualFile1DocxTemplateGenerator,
)


def representative_values(project_root: Path) -> dict[str, str]:
    """Read the existing regression fixture without duplicating its large mapping."""
    test_path = project_root / "tests" / "unit" / "test_two_member_individual_file1.py"
    tree = ast.parse(test_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "test_generator_uses_file1_and_file2_and_preserves_source_templates":
            continue
        for child in node.body:
            if not isinstance(child, ast.Assign):
                continue
            is_values = any(
                isinstance(target, ast.Name) and target.id == "values"
                for target in child.targets
            )
            if is_values:
                values = ast.literal_eval(child.value)
                if isinstance(values, dict):
                    return {str(key): str(value) for key, value in values.items()}
    raise RuntimeError("Representative two-member values were not found")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    template_dir = (
        project_root
        / "assets"
        / "templates"
        / "word"
        / "business_registration"
        / TWO_MEMBER_INDIVIDUAL_TEMPLATE_RELATIVE_DIR
    )
    result = TwoMemberIndividualFile1DocxTemplateGenerator(
        template_dir,
        args.output_dir,
    ).generate(representative_values(project_root), "phase3-qa", args.output_dir)
    if len(result.generated) != 6:
        raise RuntimeError(f"Expected 6 generated documents, got {len(result.generated)}")
    for item in result.generated:
        print(item.output_path)
    if result.unresolved:
        print("Unresolved placeholders:")
        for template_name, placeholders in sorted(result.unresolved.items()):
            print(f"- {template_name}: {', '.join(placeholders)}")
    else:
        print("Unresolved placeholders: none")


if __name__ == "__main__":
    main()
