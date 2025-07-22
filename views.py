from django.shortcuts import render
from .forms import ResumeForm
from .ml_model.predict import predict_resume_category
from .ml_model.file_utilis import extract_text_from_file
from .ml_model.recommender import calculate_match_score, get_suggestions
import logging
import re

logger = logging.getLogger(__name__)

def get_job_data(cleaned_data):
    """
    Extracts and cleans job-related data from form cleaned_data.
    """
    return {
        'title': cleaned_data.get('job_title', '').strip(),
        'skills': cleaned_data.get('job_skills', '').strip(),
        'experience': cleaned_data.get('job_experience') or 0,
        'education': cleaned_data.get('job_education', '').strip(),
        'certifications': cleaned_data.get('job_certifications', '').strip(),
    }

def extract_resume_data(text):
    """
    Naive resume data extractor from raw text.
    You can improve with real NLP or regex parsing later.
    """
    text_lower = text.lower()

    # Extract title from keywords
    title_keywords = ['manager', 'engineer', 'developer', 'analyst', 'consultant', 'specialist', 'architect']
    title = next((word.capitalize() for word in title_keywords if word in text_lower), '')

    # Extract skills by keyword presence
    skills_list = ['python', 'java', 'sql', 'aws', 'docker', 'linux', 'javascript', 'c++', 'project management']
    skills = ' '.join(skill for skill in skills_list if skill in text_lower)

    # Extract experience (e.g. "3 years", "5+ years")
    experience = 0
    match = re.search(r'(\d+(\.\d+)?)\s*\+?\s*years', text_lower)
    if match:
        try:
            experience = float(match.group(1))
        except ValueError:
            experience = 0

    # Extract education keywords
    education_keywords = ['bachelor', 'master', 'phd', 'diploma', 'degree', 'associate']
    education = next((word.capitalize() for word in education_keywords if word in text_lower), '')

    # Extract certifications keywords
    cert_keywords = ['aws', 'pmp', 'cisco', 'scrum', 'six sigma']
    certifications = ' '.join(cert for cert in cert_keywords if cert in text_lower)

    return {
        'title': title,
        'skills': skills,
        'experience': experience,
        'education': education,
        'certifications': certifications
    }

def home(request):
    results = []
    error = None

    if request.method == 'POST':
        files = request.FILES.getlist('resume_files')
        form = ResumeForm(request.POST, files=files)

        if form.is_valid():
            resume_text = form.cleaned_data.get('resume_text')
            resume_files = form.cleaned_data.get('resume_files')  # validated list

            all_resume_texts = []

            # Extract text from each uploaded file
            if resume_files:
                for file in resume_files:
                    try:
                        text = extract_text_from_file(file)
                        if text.strip():
                            all_resume_texts.append(text)
                        else:
                            logger.warning(f"No text extracted from {file.name}")
                    except Exception as e:
                        logger.error(f"Text extraction failed for {file.name}: {e}")
                        form.add_error('resume_files', f"Error extracting text from {file.name}: {str(e)}")

            # Add pasted resume text if present
            if resume_text and resume_text.strip():
                all_resume_texts.append(resume_text.strip())

            if not all_resume_texts:
                error = "No resume text found. Please upload files or paste resume content."
                return render(request, 'recommender/home.html', {'form': form, 'error': error})

            job_data = get_job_data(form.cleaned_data)

            # Process each resume and calculate score and suggestions
            for idx, text in enumerate(all_resume_texts):
                try:
                    category = predict_resume_category(text)
                    resume_data = extract_resume_data(text)
                    match_score = calculate_match_score(resume_data, job_data)
                    suggestions = get_suggestions(resume_data, job_data)

                    results.append({
                        'index': idx + 1,
                        'category': category,
                        'match_score': match_score,
                        'suggestions': suggestions,
                        'raw_text': text[:500]  # snippet for preview
                    })

                except Exception as e:
                    logger.error(f"Error processing resume #{idx + 1}: {e}")
                    results.append({
                        'index': idx + 1,
                        'error': f"Failed to process resume #{idx + 1}: {str(e)}"
                    })

            # Sort results by match_score descending (skip those with errors)
            if results:
                valid_results = [r for r in results if 'match_score' in r]
                error_results = [r for r in results if 'error' in r]
                valid_results.sort(key=lambda x: x['match_score'], reverse=True)
                results = valid_results + error_results

        else:
            error = "Form data is invalid. Please correct the errors and try again."
            logger.warning(f"Form errors: {form.errors}")

    else:
        form = ResumeForm()

    return render(request, 'recommender/home.html', {
        'form': form,
        'results': results or None,
        'error': error
    })