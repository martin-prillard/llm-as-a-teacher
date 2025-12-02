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
        prompt = f"""You are a STRICT and RIGOROUS code evaluator. Your task is to evaluate a GitHub project against a project description and provide a score from 0 to 100.

CRITICAL EVALUATION PRINCIPLES:
1. You must evaluate the project STRICTLY and RIGOROUSLY based on the requirements specified in the project description
2. Be STRICT: Only award points for requirements that are FULLY and CORRECTLY implemented
3. Partial implementations should receive PARTIAL credit only (e.g., 50% if half-complete, 0% if not functional)
4. Missing requirements should receive 0 points
5. Do NOT be lenient - the grade must TRULY reflect the work done in relation to the expected objectives
6. Do NOT apply generic best practices, coding standards, or criteria that are not explicitly mentioned in the project description

PROJECT DESCRIPTION:
{description}

REPOSITORY INFORMATION:
- Name: {repo_info.get('name', 'Unknown')}
- Language: {repo_info.get('language', 'Unknown')}
- URL: {repo_info.get('url', 'Unknown')}

SOURCE CODE:
{code_context}

EVALUATION INSTRUCTIONS:
1. Extract ALL requirements, features, and expectations from the project description
2. Create a comprehensive list of evaluation criteria based on these requirements
3. Analyze the source code to determine which requirements are implemented and to what extent
4. For EACH requirement/criterion, create a detailed assessment showing:
   - What was expected (from project description)
   - What was actually done (from code analysis)
   - Points awarded (0-100% of the points allocated to this requirement)
   - Detailed justification for the points awarded
5. Calculate the final score by summing the points for all requirements (weighted appropriately)
6. Be STRICT: If a requirement is missing, incomplete, or non-functional, award minimal or zero points
7. The final score must accurately reflect the percentage of requirements that are fully met

REQUIRED RESPONSE FORMAT (JSON):
{{
    "score": <number between 0 and 100, calculated strictly based on requirements met>,
    "explanation": "<detailed explanation that MUST include a table showing each requirement, expected work, actual work done, points awarded, and justification>",
    "evaluation_table": [
        {{
            "requirement": "<requirement/criterion 1 from project description>",
            "expected": "<what was expected for this requirement>",
            "actual": "<what was actually implemented (be specific, reference code)>",
            "points_awarded": <points out of total points for this requirement>,
            "points_possible": <total points allocated to this requirement>,
            "justification": "<detailed explanation of why these points were awarded>"
        }},
        {{
            "requirement": "<requirement/criterion 2>",
            "expected": "<what was expected>",
            "actual": "<what was actually implemented>",
            "points_awarded": <points>,
            "points_possible": <points>,
            "justification": "<explanation>"
        }}
    ],
    "summary": {{
        "total_points_awarded": <sum of all points_awarded>,
        "total_points_possible": <sum of all points_possible>,
        "requirements_fully_met": <count>,
        "requirements_partially_met": <count>,
        "requirements_not_met": <count>
    }}
}}

EXPLANATION FORMAT REQUIREMENTS:
The explanation field MUST include:
1. A clear markdown table with columns: Requirement | Expected | Actual Work Done | Points Awarded | Justification
2. For each requirement, specific references to code (file names, function names, line numbers if relevant)
3. Clear indication of what is missing, incomplete, or incorrect
4. A summary explaining how the final score was calculated

Be STRICT and RIGOROUS. The grade must truly reflect the work done. Provide your evaluation in valid JSON format:"""
        
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
                        "content": "You are a strict and rigorous code evaluator. Always respond with valid JSON. Be strict in your evaluation - only award points for requirements that are fully and correctly implemented."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for more consistent, strict evaluations
                max_tokens=4000  # Increased for detailed tables and explanations
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
            
            # Build detailed explanation with evaluation table
            detailed_explanation = explanation
            
            # Add evaluation table if present
            if 'evaluation_table' in data and data['evaluation_table']:
                detailed_explanation += "\n\n## 📊 Detailed Evaluation Table\n\n"
                detailed_explanation += "| Requirement | Expected | Actual Work Done | Points Awarded | Justification |\n"
                detailed_explanation += "|------------|----------|------------------|----------------|---------------|\n"
                
                for item in data['evaluation_table']:
                    req = item.get('requirement', 'N/A')
                    expected = item.get('expected', 'N/A')
                    actual = item.get('actual', 'N/A')
                    points_awarded = item.get('points_awarded', 0)
                    points_possible = item.get('points_possible', 0)
                    justification = item.get('justification', 'N/A')
                    
                    # Escape pipe characters in table cells
                    req = str(req).replace('|', '\\|')
                    expected = str(expected).replace('|', '\\|')
                    actual = str(actual).replace('|', '\\|')
                    justification = str(justification).replace('|', '\\|')
                    
                    points_str = f"{points_awarded}/{points_possible}" if points_possible > 0 else str(points_awarded)
                    detailed_explanation += f"| {req} | {expected} | {actual} | {points_str} | {justification} |\n"
            
            # Add summary if present
            if 'summary' in data and data['summary']:
                summary = data['summary']
                detailed_explanation += "\n\n## 📈 Evaluation Summary\n\n"
                detailed_explanation += f"- **Total Points Awarded**: {summary.get('total_points_awarded', 0)}\n"
                detailed_explanation += f"- **Total Points Possible**: {summary.get('total_points_possible', 0)}\n"
                detailed_explanation += f"- **Requirements Fully Met**: {summary.get('requirements_fully_met', 0)}\n"
                detailed_explanation += f"- **Requirements Partially Met**: {summary.get('requirements_partially_met', 0)}\n"
                detailed_explanation += f"- **Requirements Not Met**: {summary.get('requirements_not_met', 0)}\n"
            
            # Keep backward compatibility with old format
            if 'strengths' in data and data['strengths']:
                detailed_explanation += "\n\n### ✅ Strengths:\n"
                for strength in data['strengths']:
                    detailed_explanation += f"- {strength}\n"
            
            if 'weaknesses' in data and data['weaknesses']:
                detailed_explanation += "\n\n### ❌ Weaknesses:\n"
                for weakness in data['weaknesses']:
                    detailed_explanation += f"- {weakness}\n"
            
            if 'missing_features' in data and data['missing_features']:
                detailed_explanation += "\n\n### ⚠️ Missing Features:\n"
                for feature in data['missing_features']:
                    detailed_explanation += f"- {feature}\n"
            
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

