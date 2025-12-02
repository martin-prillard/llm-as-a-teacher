#!/usr/bin/env python3
"""
Gradio web application for the LLM-based GitHub project evaluator.
"""

import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import gradio as gr

# Load environment variables from .env file
load_dotenv()

from evaluator import ProjectEvaluator
from file_parser import FileParser
from git_handler import GitHandler


def evaluate_project(
    git_url: str,
    api_key: str,
    description_file,
    description_text: str
):
    """
    Evaluate a GitHub project against a project description.
    
    Args:
        git_url: GitHub repository URL
        api_key: OpenAI API key
        description_file: Uploaded file object
        description_text: Text description input
        
    Returns:
        Markdown string with evaluation results
    """
    try:
        # Validate inputs
        if not git_url or not git_url.strip():
            return "❌ Error: GitHub URL is required"
        
        api_key = api_key.strip() if api_key else os.getenv('OPENAI_API_KEY')
        if not api_key:
            return "❌ Error: OpenAI API key is required"
        
        # Handle description: either uploaded file or text input
        description = None
        temp_file_path = None
        
        if description_file is not None:
            # Save uploaded file temporarily
            temp_file_path = description_file.name
            
            # Parse the file
            parser = FileParser()
            description = parser.parse(temp_file_path)
        elif description_text and description_text.strip():
            description = description_text.strip()
        else:
            return "❌ Error: Project description is required (file upload or text input)"
        
        if not description:
            return "❌ Error: Could not parse project description"
        
        # Access GitHub repository
        git_handler = GitHandler()
        try:
            repo_info = git_handler.get_repository_info(git_url.strip())
            
            if not repo_info:
                return "❌ Error: Could not access GitHub repository. Please check the URL."
            
            # Evaluate the project
            evaluator = ProjectEvaluator(api_key=api_key)
            result = evaluator.evaluate(repo_info, description)
            
            # Prepare response
            repo_name = repo_info.get('name', 'Unknown')
            repo_url = repo_info.get('url', git_url)
            language = repo_info.get('language', 'Unknown')
            files_analyzed = len(repo_info.get('files', []))
            
            score = result['score']
            explanation = result['explanation']
            
            # Format the output
            output_text = f"""# 📊 Evaluation Results

## Evaluation score (0-100): {score}/100

### Repository Information
- **Repository**: [{repo_name}]({repo_url})
- **Language**: {language}
- **Files Analyzed**: {files_analyzed}

### 📝 Detailed Evaluation

{explanation}
"""
            
            return output_text
        finally:
            # Clean up
            git_handler.cleanup()
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return f"❌ Error: {error_msg}"


def create_interface():
    """Create and configure the Gradio interface."""
    
    with gr.Blocks(title="LLM as a Teacher - Project Evaluator") as demo:
        # CSS to hide the Gradio footer
        gr.HTML(
            value="<style>footer {display: none !important;} .gradio-footer {display: none !important;}</style>",
            visible=False
        )
        
        gr.Markdown(
            """
            # 🤖 LLM as a Teacher
            ## Evaluate GitHub Projects with AI
            
            Upload a project description or paste it as text, then evaluate any GitHub repository against it.
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                git_url = gr.Textbox(
                    label="GitHub Repository URL *",
                    placeholder="https://github.com/username/repository"
                )
                gr.Markdown("*Enter the full URL of the GitHub repository to evaluate*")
                
                api_key = gr.Textbox(
                    label="OpenAI API Key *",
                    type="password",
                    placeholder="sk-...",
                    value=os.getenv('OPENAI_API_KEY', '')
                )
                gr.Markdown("*Your OpenAI API key for LLM evaluation*")
                
                with gr.Tabs():
                    with gr.Tab("Upload File"):
                        description_file = gr.File(
                            label="Project Description File",
                            file_types=[".pdf", ".docx", ".doc", ".txt", ".md"]
                        )
                        gr.Markdown("*Supported formats: PDF, Word (.docx), Text (.txt, .md)*")
                    
                    with gr.Tab("Text Input"):
                        description_text = gr.Textbox(
                            label="Project Description",
                            placeholder="Paste or type the project description here...",
                            lines=10
                        )
                        gr.Markdown("*Enter the project description as text*")
                
                evaluate_btn = gr.Button("Evaluate Project", variant="primary", size="lg")
                
                gr.Markdown("---")
                gr.Markdown(
                    """
                    ### Evaluation Criteria
                    
                    The evaluation is **strictly based on the expected requirements** specified in the uploaded project description file. The tool evaluates projects by:
                    
                    1. **Extracting Requirements**: Parses the project description to identify all specified requirements, features, and expectations
                    2. **Code Analysis**: Analyzes the source code from the GitHub repository
                    3. **Requirement Matching**: Compares the implemented code against each requirement from the project description
                    4. **Scoring**: Generates a score (0-100) based solely on how well the code meets the requirements specified in the project description
                    
                    **Important**: The evaluation focuses exclusively on whether the code fulfills the requirements stated in the project description. It does not apply generic best practices or criteria that are not mentioned in the project description.
                    """
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### Evaluation Results")
                results_output = gr.Markdown(
                    value="Results will appear here after evaluation..."
                )
        
        # Set up the evaluation function
        evaluate_btn.click(
            fn=evaluate_project,
            inputs=[git_url, api_key, description_file, description_text],
            outputs=[results_output]
        )
    
    return demo


if __name__ == '__main__':
    port = int(os.getenv('PORT', 7860))
    share = os.getenv('GRADIO_SHARE', 'False').lower() == 'true'
    
    demo = create_interface()
    demo.launch(
        server_name='0.0.0.0',
        server_port=port,
        share=share
    )
