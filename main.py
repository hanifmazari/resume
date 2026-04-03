from src.BestResumeMaker import logger
logger.info("welcome to the resumemaker")

# Import all template functions
from src.BestResumeMaker.template.modern.modern01 import modern1
from src.BestResumeMaker.template.modern.modern02 import modern2
from src.BestResumeMaker.template.modern.modern03 import modern3
from src.BestResumeMaker.template.modern.modern04 import modern4
from src.BestResumeMaker.template.modern.modern05 import modern5
from src.BestResumeMaker.template.modern.modern06 import modern6
from src.BestResumeMaker.template.modern.modern07 import modern7
from src.BestResumeMaker.template.modern.modern08 import modern8
from src.BestResumeMaker.template.modern.modern09 import modern9
from src.BestResumeMaker.template.modern.modern_10 import modern10
from src.BestResumeMaker.template.professional.prof_01 import professional1
from src.BestResumeMaker.template.professional.prof_02 import professional2
from src.BestResumeMaker.template.professional.prof_03 import professional3
from src.BestResumeMaker.template.professional.prof_04 import professional4
from src.BestResumeMaker.template.professional.prof_05 import professional5
from src.BestResumeMaker.template.professional.prof_06 import professional6
from src.BestResumeMaker.template.professional.prof_07 import professional7
from src.BestResumeMaker.template.professional.prof_08 import professional8
from src.BestResumeMaker.components.ai_helper import analyze_resume_against_jd
from datetime import datetime

def generate_resume(
    template_name,
    personal_info,
    professional_summary,
    work_experience,
    education,
    skills,
    profile_picture = None,
    academic_projects=None,
    certifications=None,
    publications=None,
    hobbies=None,
    languages=None,
    referees=None,
    output_file="resume.pdf",
    page_size="A4"
):
    """
    Generate a resume using the specified template.
    
    Args:
        template_name (str): Name of the template to use (e.g., 'modern1', 'professional2')
        personal_info (dict): Personal information
        professional_summary (str): Professional summary text
        work_experience (list): Work experience data
        education (list): Education data
        skills (list): Skills list
        academic_projects (list, optional): Academic projects data
        certifications (list, optional): Certifications data
        publications (list, optional): Publications data
        hobbies (list, optional): Hobbies list
        languages (list, optional): Languages list
        referees (list, optional): References data
        output_file (str): Output PDF filename
        page_size (str): Page size for the PDF
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Template mapping dictionary
    template_mapping = {
        'modern1': modern1,
        'modern2': modern2,
        'modern3': modern3,
        'modern4': modern4,
        'modern5': modern5,
        'modern6': modern6,
        'modern7': modern7,
        'modern8': modern8,
        'modern9': modern9,
        'modern10': modern10,
        'professional1': professional1,
        'professional2': professional2,
        'professional3': professional3,
        'professional4': professional4,
        'professional5': professional5,
        'professional6': professional6,
        'professional7': professional7,
        'professional8': professional8,
    }
    
    # Check if template exists
    if template_name not in template_mapping:
        available_templates = list(template_mapping.keys())
        logger.error(f"Template '{template_name}' not found. Available templates: {available_templates}")
        raise ValueError(f"Template '{template_name}' not found. Available templates: {available_templates}")
    
    # Get the template function
    template_function = template_mapping[template_name]
    
    try:
        # Prepare arguments for the template function
        template_args = {
            'personal_info': personal_info,
            'professional_summary': professional_summary,
            'work_experience': work_experience,
            'education': education,
            'skills': skills,
            'output_file': output_file,
            'page_size': page_size
        }
        
        # Add optional parameters if they are provided
        if profile_picture is not None:
            template_args['profile_picture'] = profile_picture
        if academic_projects is not None:
            template_args['academic_projects'] = academic_projects
        if certifications is not None:
            template_args['certifications'] = certifications
        if publications is not None:
            template_args['publications'] = publications
        if hobbies is not None:
            template_args['hobbies'] = hobbies
        if languages is not None:
            template_args['languages'] = languages
        if referees is not None:
            template_args['referees'] = referees
        
        # Call the template function
        template_function(**template_args)
        logger.info(f"Resume generated successfully using template '{template_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Error generating resume with template '{template_name}': {str(e)}")
        return False