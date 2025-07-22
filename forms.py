from django import forms

class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class ResumeForm(forms.Form):
    resume_files = forms.FileField(
        widget=MultiFileInput(attrs={
            'multiple': True,
            'accept': '.pdf,.doc,.docx,.txt'
        }),
        required=False,
        label="Upload Resume Files",
        help_text="Accepted formats: PDF, DOC, DOCX, TXT. Max size: 5MB per file."
    )

    resume_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Paste your resume text here...',
            'rows': 6
        }),
        required=False,
        label="Paste Resume Text"
    )

    job_title = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Software Engineer'}),
        label="Job Title"
    )

    job_skills = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'e.g. Python, Django, SQL'}),
        required=False,
        label="Required Skills"
    )

    job_experience = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'placeholder': 'Years of experience'}),
        label="Minimum Experience (Years)"
    )

    job_education = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. BSc Computer Science'}),
        label="Required Education"
    )

    job_certifications = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'e.g. AWS Certified, PMP'}),
        required=False,
        label="Preferred Certifications"
    )

    def __init__(self, *args, **kwargs):
        # Accept uploaded files from the view to validate multiple files
        self.uploaded_files = kwargs.pop('files', None)
        super().__init__(*args, **kwargs)

    def clean_resume_files(self):
        files = self.uploaded_files or []
        if not files:
            return None

        valid_mime_types = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
        }

        for file in files:
            if file.content_type not in valid_mime_types:
                raise forms.ValidationError(
                    f"Unsupported file type: {file.content_type}. Only PDF, DOC, DOCX, TXT are allowed."
                )
            if file.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError(
                    f"File '{file.name}' exceeds the 5MB size limit."
                )
        return files

    def clean(self):
        cleaned_data = super().clean()
        resume_text = cleaned_data.get('resume_text')
        resume_files = self.uploaded_files or []

        # Ensure either resume text or at least one file is provided
        if not resume_text and not resume_files:
            raise forms.ValidationError(
                "Please provide either pasted resume text or upload at least one resume file."
            )

        # If resume text is provided, require some job detail fields
        if resume_text:
            required_if_text = ['job_title', 'job_skills', 'job_experience']
            for field in required_if_text:
                if not cleaned_data.get(field):
                    self.add_error(field, "This field is required when pasting resume text.")

        return cleaned_data