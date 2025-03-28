from dotenv import load_dotenv
load_dotenv()

import os

from google import genai
from google.genai import types
import os
import time
import pathlib

resume_path = os.getenv('DEFAULT_RESUME_PATH')
pdf_file = pathlib.Path(resume_path)


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

class CustomResumeHandler():
    def __init__(self,  base_resume_file_path=pdf_file, resume_dir='custom_resumes', ):
        self.resume_dir = resume_dir
        self.current_job_description = None
        self.current_job_id = None  # Add this to track the current job
        self.base_resume_file = base_resume_file_path
        # Create resume directory if it doesn't exist
        os.makedirs(self.resume_dir, exist_ok=True)
        

    def generate_custom_resume(self, job_title, company_name, job_description):
        """Generate a custom resume based on the job description using Gemini."""
        print(f"\nGenerating custom resume for: {job_title} at {company_name}")

        # Create a unique job ID with sanitized company name
        company_name = self.sanitize_filename(company_name)
        job_title = self.sanitize_filename(job_title)  # Use the sanitize function
        self.current_job_id = f"{company_name}_{job_title}"

        prompt = f""""

I'm applying to a job with the following description:
({job_description})

You are an expert resume writer and ATS optimization specialist. Your task is to create a highly effective, ATS-friendly resume in Markdown format based on the provided job description and attached resume. Follow these guidelines:

1. Analyze the job description for key skills, qualifications, and keywords.
2. Review the existing resume for relevant experience and achievements.
3. Create a new resume that aligns the candidate's qualifications with the job requirements.
4. Use the following structure, formatting it in Markdown:

# [Candidate Name]
[City, State] | [Phone] | [Email] | [LinkedIn]

## Professional Summary
[Concise 2-3 sentence summary tailored to the job description]

## Core Competencies
- [Skill 1]
- [Skill 2]
- [Skill 3]
[List 6-8 key ]

## Professional Experience

### [Job Title], [Company Name]
[Start Date] - [End Date]

- [Achievement/responsibility using action verb and metrics]
- [Achievement/responsibility using action verb and metrics]
- [Achievement/responsibility using action verb and metrics]


[Repeat for each relevant position, focusing on the most recent and relevant roles]

## Education

**[Degree], [Major]**
[University Name], [Location]
[Graduation Date]

## Technical Skills
[List relevant technical skills, separated by commas]

Please generate a tailored, ATS-optimized resume based on these guidelines, the provided job description, and the candidate's existing resume

5. Ensure the resume is concise, typically fitting two pages maximum for extensive experience.
6. Ensure most recent job contains at least one acheivement that can be related to what the job description is looking for, generate a project if need be, but it must also make sense to the current position.
7. Professional summary should tie current skills to job description if no direct experience is there, ensure knowledge gaps can be easily closed
8. Use bullet points for easy readability.
9. Incorporate keywords from the job description naturally throughout the resume.
10. Use action verbs and quantify achievements where possible.
11. Avoid graphics, tables, or complex formatting that may confuse ATS.
12. Use standard section headings for easy parsing by ATS.
13. pretend you are being called like an API endpoint and your payload(reponse) is being directly ported into an .md file, every line has to translate correctly as a markdown file.
14. My linkedin is https://www.linkedin.com/in/dankazaman/
15. DO NOT ADD ANY '```markdown' and '```' LINES IN YOUR RESPONSE
"""


        try:
            # Request customized resume from Gemini
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[
                    types.Part.from_bytes(
                        data=self.base_resume_file.read_bytes(),
                        mime_type='application/pdf',
                    ),
                    prompt
                ]
            )

            # Save the custom resume
            custom_resume_content = response.text.strip()
            self._save_custom_resume(custom_resume_content)

            return self.current_job_id

        except Exception as e:
            print(f"Error generating custom resume: {e}")
            return None

    def _save_custom_resume(self, resume_content):
        """Save the custom resume as both markdown and PDF."""
        if not self.current_job_id:
            print("No job ID set, can't save resume")
            return False
            
        # Save markdown version
        md_path = os.path.join(self.resume_dir, f"{self.current_job_id}.md")
        with open(md_path, 'w') as f:
            f.write(resume_content)
        
        # Convert to PDF using a library like mdpdf or pypandoc
        # This is a placeholder - you'll need to implement the actual conversion
        pdf_path = os.path.join(self.resume_dir, f"{self.current_job_id}.pdf")
        self._convert_markdown_to_pdf(md_path, pdf_path)
        
        print(f"Custom resume saved to {pdf_path}")
        return pdf_path

    def _convert_markdown_to_pdf(self, markdown_path, pdf_path):
        """Convert markdown to PDF with optimizations for 2-page limit."""
        import markdown
        import weasyprint
        from bs4 import BeautifulSoup
        import io

        # Read Markdown content
        with open(markdown_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Convert to HTML
        html_content = markdown.markdown(md_content, extensions=['extra'])

        # More compact CSS for fitting content into 2 pages
        compact_css = '''
        @page {
            size: letter;
            margin: 0.75cm;
        }
        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 9pt;
            line-height: 1.3;
            color: #333;
        }
        h1 {
            font-size: 14pt;
            margin-bottom: 0.2cm;
            border-bottom: 1px solid #999;
            padding-bottom: 0.1cm;
        }
        h2 {
            font-size: 11pt;
            margin-top: 0.3cm;
            margin-bottom: 0.2cm;
            color: #444;
        }
        ul {
            margin-top: 0.1cm;
            margin-bottom: 0.3cm;
            padding-left: 0.8cm;
        }
        li {
            margin-bottom: 0.1cm;
        }
        p {
            margin-top: 0.05cm;
            margin-bottom: 0.2cm;
        }
        .header {
            text-align: center;
            margin-bottom: 0.3cm;
        }
        .contact {
            text-align: center;
            font-size: 8pt;
            margin-bottom: 0.3cm;
        }
        /* Make bullet lists more compact */
        ul li {
            padding-left: 0;
        }
        /* Two-column layout for skills section */
        .skills-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
        }
        .skill-column {
            width: 48%;
        }
        '''

        # Process HTML to optimize space
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find the Key Skills section and convert it to a two-column layout if needed
        skills_section = None
        for h2 in soup.find_all('h2'):
            if 'Key Skills' in h2.text:
                skills_section = h2
                break
            
        if skills_section and skills_section.find_next('ul'):
            skills_list = skills_section.find_next('ul')

            # Create a container div
            container_div = soup.new_tag('div')
            container_div['class'] = 'skills-container'

            # Create two column divs
            col1 = soup.new_tag('div')
            col1['class'] = 'skill-column'
            col2 = soup.new_tag('div')
            col2['class'] = 'skill-column'

            # Split the skills list items between columns
            list_items = skills_list.find_all('li')
            half = len(list_items) // 2

            # Create two new lists
            ul1 = soup.new_tag('ul')
            ul2 = soup.new_tag('ul')

            for i, li in enumerate(list_items):
                if i < half:
                    ul1.append(li.extract())
                else:
                    ul2.append(li.extract())

            col1.append(ul1)
            col2.append(ul2)

            container_div.append(col1)
            container_div.append(col2)

            # Replace the original list with our container
            skills_list.replace_with(container_div)

        # Create complete HTML document with CSS
        html_doc = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Resume</title>
            <style>
                {compact_css}
            </style>
        </head>
        <body>
            {soup}
        </body>
        </html>
        '''

        # First attempt - generate PDF with initial settings
        html = weasyprint.HTML(string=html_doc)
        pdf_bytes = html.write_pdf()

        # A simple heuristic to estimate page count based on PDF size
        # This isn't perfect but can give us a rough idea without parsing the PDF
        pdf_size = len(pdf_bytes)
        estimated_pages = max(1, pdf_size // 30000)  # Rough estimate

        # If we estimate more than 2 pages, try again with more compact settings
        if estimated_pages > 2:
            print(f"Estimated {estimated_pages} pages. Trying more compact settings...")

            # Even more compact CSS
            smaller_css = compact_css.replace('font-size: 9pt;', 'font-size: 8.5pt;')
            smaller_css = smaller_css.replace('font-size: 14pt;', 'font-size: 13pt;')
            smaller_css = smaller_css.replace('font-size: 11pt;', 'font-size: 10pt;')
            smaller_css = smaller_css.replace('margin: 0.75cm;', 'margin: 0.65cm;')
            smaller_css = smaller_css.replace('line-height: 1.3;', 'line-height: 1.2;')

            html_doc = html_doc.replace(compact_css, smaller_css)
            html = weasyprint.HTML(string=html_doc)
            pdf_bytes = html.write_pdf()

            # If still potentially too long, try even smaller settings
            pdf_size = len(pdf_bytes)
            if pdf_size // 30000 > 2:
                print("Still too long. Using minimum size settings...")

                # Minimum viable size settings
                minimal_css = smaller_css.replace('font-size: 8.5pt;', 'font-size: 8pt;')
                minimal_css = minimal_css.replace('margin: 0.65cm;', 'margin: 0.5cm;')
                minimal_css = minimal_css.replace('line-height: 1.2;', 'line-height: 1.1;')

                html_doc = html_doc.replace(smaller_css, minimal_css)
                html = weasyprint.HTML(string=html_doc)
                pdf_bytes = html.write_pdf()

        # Write the final version to the output file
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)

        print(f"Successfully converted {markdown_path} to {pdf_path}")
        return pdf_path

    def sanitize_filename(self, name):
        # Remove characters that are not allowed in filenames
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name

if __name__ == "__main__":
    from generic_application import GenericApplier

    test = CustomResumeHandler()
    applier = GenericApplier()
    url = "https://jobs.multicoin.capital/companies/paxos/jobs/47411676-software-engineer-financial-automation"
    job_description = applier.get_job_description_from_url(url)
    print(job_description)
    test.generate_custom_resume("sde", "paxos", job_description)



