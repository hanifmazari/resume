import requests
import json


def analyze_resume():
    """Analyze a resume against a job description"""
    # Job description for analysis
    job_description = """
    Senior Software Engineer
    Requirements:
    - 5+ years of experience in software development
    - Proficient in Python and JavaScript
    - Experience with React and Django
    - Knowledge of AWS and cloud services
    - Experience with Docker and containerization
    - Excellent problem-solving skills
    """
    
    # Create multipart form data
    files = {'resume': open('generated_resume.pdf', 'rb')}
    data = {'job_description': job_description}
    
    # Send request to analyze resume
    response = requests.post(
        'https://bestresumemaker.onrender.com/analyze-resume',
        # 'http://localhost:8000/analyze-resume',
        files=files,
        data=data
    )
    
    # Check if the request was successful
    if response.status_code == 200:
        result = response.json()
        print(f"Match Score: {result.get('JD Match', '0%')}")
        print(f"Assessment: {result.get('assessment', '')}")
        print("Missing Keywords:")
        for keyword in result.get('MissingKeywords', []):
            print(f"- {keyword}")
    else:
        print(f"Error: {response.json()}")

if __name__ == "__main__":
    analyze_resume()