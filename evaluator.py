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

PROJECT DESCRIPTION:
{description}

REPOSITORY INFORMATION:
- Name: {repo_info.get('name', 'Unknown')}
- Language: {repo_info.get('language', 'Unknown')}
- URL: {repo_info.get('url', 'Unknown')}

SOURCE CODE:
{code_context}

EVALUATION CRITERIA:
1. Functionality: Does the code implement the features described in the project description?
2. Code Quality: Is the code well-structured, readable, and follows best practices?
3. Completeness: Are all required components present and functional?
4. Architecture: Is the project structure appropriate for the described functionality?
5. Documentation: Is there adequate documentation (comments, README, etc.)?

INSTRUCTIONS:
1. Analyze the source code against the project description
2. Evaluate each criterion above
3. Provide a score from 0 to 100 (where 100 is perfect alignment with the description)
4. Write a detailed explanation justifying your score
5. Highlight specific strengths and weaknesses
6. Mention any missing features or areas for improvement

RESPONSE FORMAT (JSON):
{{
    "score": <number between 0 and 100>,
    "explanation": "<detailed explanation of the evaluation>",
    "strengths": ["<strength 1>", "<strength 2>", ...],
    "weaknesses": ["<weakness 1>", "<weakness 2>", ...],
    "missing_features": ["<missing feature 1>", ...]
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

