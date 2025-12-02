"""
LLM-based project evaluator.
Evaluates GitHub projects against project descriptions.
"""

import os
from typing import Dict, Optional
import json


class ProjectEvaluator:
    """Evaluate projects using LLM."""
    
    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        """
        Initialize the evaluator.
        
        Args:
            model: LLM model to use (default: gpt-4o)
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set OPENAI_API_KEY environment variable or pass --api-key"
            )
    
    def evaluate(self, repo_info: Dict, description: str) -> Dict:
        """
        Evaluate a repository against a project description.
        
        Args:
            repo_info: Repository information dictionary
            description: Project description text
            
        Returns:
            Dictionary with 'score' (0-100) and 'explanation'
        """
        # Prepare code context
        code_context = self._prepare_code_context(repo_info)
        
        # Create evaluation prompt
        prompt = self._create_evaluation_prompt(
            repo_info,
            description,
            code_context
        )
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Parse response
        result = self._parse_response(response)
        
        return result
    
    def _prepare_code_context(self, repo_info: Dict) -> str:
        """Prepare code context from repository files."""
        files = repo_info.get('files', [])
        
        if not files:
            return "No code files found in repository."
        
        context_parts = []
        context_parts.append(f"Repository: {repo_info.get('name', 'Unknown')}")
        context_parts.append(f"Language: {repo_info.get('language', 'Unknown')}")
        context_parts.append(f"\nCode Files ({len(files)} files):\n")
        
        for file_info in files[:20]:  # Limit to 20 files
            path = file_info.get('path', file_info.get('name', 'unknown'))
            content = file_info.get('content', '')
            
            # Truncate very long files
            if len(content) > 10000:
                content = content[:10000] + "\n... (truncated)"
            
            context_parts.append(f"\n{'='*60}")
            context_parts.append(f"File: {path}")
            context_parts.append(f"{'='*60}")
            context_parts.append(content)
        
        return "\n".join(context_parts)
    
    def _create_evaluation_prompt(
        self,
        repo_info: Dict,
        description: str,
        code_context: str
    ) -> str:
        """Create the evaluation prompt for the LLM."""
        prompt = f"""You are an expert code evaluator. Your task is to evaluate a GitHub project against a project description and provide a score from 0 to 100.

CRITICAL: You must evaluate the project STRICTLY based on the requirements specified in the project description. Do NOT apply generic best practices, coding standards, or criteria that are not explicitly mentioned in the project description. Your evaluation should focus exclusively on whether the code fulfills the requirements stated in the project description.

PROJECT DESCRIPTION:
{description}

REPOSITORY INFORMATION:
- Name: {repo_info.get('name', 'Unknown')}
- Language: {repo_info.get('language', 'Unknown')}
- URL: {repo_info.get('url', 'Unknown')}

SOURCE CODE:
{code_context}

EVALUATION INSTRUCTIONS:
1. Extract all requirements, features, and expectations from the project description
2. Analyze the source code to determine which requirements are implemented
3. Compare each requirement from the project description against the implemented code
4. Provide a score from 0 to 100 based SOLELY on how well the code meets the requirements specified in the project description (where 100 means all requirements are fully met)
5. Write a detailed explanation justifying your score, referencing specific requirements from the project description
6. Highlight which requirements are met and which are missing or incomplete
7. Do NOT penalize for things not mentioned in the project description (e.g., code quality standards, architecture patterns, documentation practices that aren't required)

RESPONSE FORMAT (JSON):
{{
    "score": <number between 0 and 100>,
    "explanation": "<detailed explanation of the evaluation, referencing specific requirements from the project description>",
    "strengths": ["<requirement 1 that is well implemented>", "<requirement 2 that is well implemented>", ...],
    "weaknesses": ["<requirement 1 that is missing or incomplete>", "<requirement 2 that is missing or incomplete>", ...],
    "missing_features": ["<missing requirement 1 from project description>", ...]
}}

Provide your evaluation in valid JSON format:"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API."""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code evaluator. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        except ImportError:
            raise ImportError(
                "OpenAI library is required. Install with: pip install openai"
            )
        except Exception as e:
            raise Exception(f"Error calling LLM: {str(e)}")
    
    def _parse_response(self, response: str) -> Dict:
        """Parse LLM response and extract score and explanation."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
            
            # Parse JSON
            data = json.loads(response)
            
            score = int(data.get('score', 0))
            # Ensure score is between 0 and 100
            score = max(0, min(100, score))
            
            explanation = data.get('explanation', 'No explanation provided.')
            
            # Build detailed explanation
            detailed_explanation = explanation
            
            if 'strengths' in data and data['strengths']:
                detailed_explanation += "\n\nStrengths:"
                for strength in data['strengths']:
                    detailed_explanation += f"\n- {strength}"
            
            if 'weaknesses' in data and data['weaknesses']:
                detailed_explanation += "\n\nWeaknesses:"
                for weakness in data['weaknesses']:
                    detailed_explanation += f"\n- {weakness}"
            
            if 'missing_features' in data and data['missing_features']:
                detailed_explanation += "\n\nMissing Features:"
                for feature in data['missing_features']:
                    detailed_explanation += f"\n- {feature}"
            
            return {
                'score': score,
                'explanation': detailed_explanation
            }
        except json.JSONDecodeError:
            # Fallback: try to extract score and explanation from text
            import re
            
            # Try to find score
            score_match = re.search(r'score["\']?\s*[:=]\s*(\d+)', response, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else 50
            
            # Use the response as explanation
            return {
                'score': max(0, min(100, score)),
                'explanation': response
            }

