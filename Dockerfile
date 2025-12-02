# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir \
    openai>=1.0.0 \
    requests>=2.31.0 \
    gradio>=4.0.0 \
    pdfplumber>=0.10.0 \
    python-docx>=1.1.0 \
    python-dotenv>=1.0.0

# Copy application files
COPY app.py evaluator.py file_parser.py git_handler.py main.py ./

# Expose the port Gradio runs on
EXPOSE 7860

# Set environment variables
ENV PORT=7860
ENV GRADIO_SHARE=False

# Run the application
CMD ["python", "app.py"]

