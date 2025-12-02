#!/usr/bin/env python3
"""
Main entry point for the LLM-based GitHub project evaluator.
Evaluates student GitHub projects against project descriptions.
"""

import argparse
import sys
from pathlib import Path
from evaluator import ProjectEvaluator
from file_parser import FileParser
from git_handler import GitHandler


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a GitHub project against a project description using LLM"
    )
    parser.add_argument(
        "git_url",
        type=str,
        help="URL of the GitHub repository to evaluate"
    )
    parser.add_argument(
        "description_file",
        type=str,
        help="Path to the project description file (PDF, Word, or text)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for the evaluation report (optional)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="LLM model to use for evaluation (default: gpt-4o)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API key (or set OPENAI_API_KEY environment variable)"
    )
    
    args = parser.parse_args()
    
    try:
        # Parse the project description
        print("📄 Parsing project description...")
        parser_obj = FileParser()
        description = parser_obj.parse(args.description_file)
        
        if not description:
            print("❌ Error: Could not parse project description file.")
            sys.exit(1)
        
        print(f"✅ Project description parsed ({len(description)} characters)")
        
        # Handle git repository
        print("🔍 Accessing GitHub repository...")
        git_handler = GitHandler()
        try:
            repo_info = git_handler.get_repository_info(args.git_url)
            
            if not repo_info:
                print("❌ Error: Could not access GitHub repository.")
                return 1
            
            print(f"✅ Repository accessed: {repo_info.get('name', 'Unknown')}")
            
            # Evaluate the project
            print("🤖 Evaluating project with LLM...")
            evaluator = ProjectEvaluator(
                model=args.model,
                api_key=args.api_key
            )
            
            result = evaluator.evaluate(repo_info, description)
            
            # Display results
            print("\n" + "="*60)
            print("📊 EVALUATION RESULTS")
            print("="*60)
            print(f"\n🎯 Score: {result['score']}/100")
            print(f"\n📝 Explanation:\n{result['explanation']}")
            print("\n" + "="*60)
            
            # Save to file if requested
            if args.output:
                output_path = Path(args.output)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("EVALUATION REPORT\n")
                    f.write("="*60 + "\n\n")
                    f.write(f"Repository: {args.git_url}\n")
                    f.write(f"Description File: {args.description_file}\n")
                    f.write(f"Score: {result['score']}/100\n\n")
                    f.write("Explanation:\n")
                    f.write(result['explanation'])
                print(f"\n💾 Report saved to: {output_path}")
            
            return 0
        finally:
            # Clean up temporary directories
            git_handler.cleanup()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

