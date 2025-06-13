# Update imports - only need PROMPTS now

# Update imports - only need PROMPTS now
from dotenv import load_dotenv
load_dotenv()

import os
from google import genai
from google.genai import types
import pathlib

# Import from config - removed RESUME_GENERATION
from src.config.config import DEFAULT_RESUME_PATH, RESUME_DIR, GEMINI_API_KEY, PROMPTS

# Use values from config instead of directly from environment variables
resume_path = DEFAULT_RESUME_PATH
pdf_file = pathlib.Path(resume_path)

class CustomResumeHandler():
    def __init__(self, base_resume_file_path=pdf_file, resume_dir=RESUME_DIR):
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
        print(self.current_job_id, "current job id")
        # Get the prompt template from config and format it with just the job description
        prompt = PROMPTS["RESUME_GENERATION"].format(
            job_description=job_description
        )

        try:
            # Request customized resume from Gemini using API key from config
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
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|', '\n', '\t', '\r', '!', '@', '#', '$', '%', '^', '&', '(', ')', '+', '=', '{', '}', '[', ']', ';', "'", ',', '.', '`']
        name = ''.join(c for c in name if c not in invalid_chars)
        name = name.replace(' ', '_')  # Replace spaces with underscores
        print(f"Sanitized filename: {name}")
        return name

if __name__ == "__main__":

     
    job_description ="""
The Opportunity

Are you passionate about crafting products that users and team members love to engage with? We're seeking an individual who is enthusiastic about the power of voice and eager to redefine communication, collaboration, and idea sharing with our AI-powered collaborative note-taking app. As our core product gains rapid adoption, this role will play a pivotal part in enhancing how people and teams communicate. The ideal candidate thrives in a fast-paced, collaborative, and agile startup environment and is committed to delivering high-quality product experiences.

Your Impact:
Develop and maintain scalable web automation frameworks using Playwright, Selenium, and Pytest to ensure comprehensive test coverage.
Define, design, and implement efficient automation strategies to reduce manual testing efforts and improve test execution speed.
Provide test automation support by writing and maintaining high-quality test code, following best coding practices, and conducting PR reviews.
Work closely with development and QA teams in an Agile environment to integrate automation early and accelerate release cycles.
Drive multiple automation initiatives in a fast-paced CI/CD environment, ensuring stable and reliable test execution.
Continuously evaluate and recommend cutting-edge automation tools to optimize testing, improve reliability, and minimize flakiness.
Build utilities and scripts to automate repetitive tasks, improving overall test efficiency and reducing execution time.
We’re looking for someone who:
5+ years of experience as an Sr SDET or Software Engineer, focusing on web application testing and automation.
Strong programming skills in Python and JavaScript/TypeScript for test automation.
Hands-on experience with Selenium, Playwright, and/or Puppeteer for browser automation.
Expertise in Pytest for writing and structuring test cases.
Solid experience with integration testing and end-to-end testing of web applications.
Strong understanding of CI/CD processes and experience integrating automation into pipelines using Jenkins, GitHub Actions, or similar tools.
Familiarity with containerization tools like Docker for creating test environments.
Experience with web performance, accessibility, and security testing best practices.
Exposure to cloud-based testing platforms such as BrowserStack or Sauce Labs.
Excellent problem-solving skills and the ability to debug and analyze test failures efficiently.
Strong communication skills with the ability to collaborate effectively in a fast-paced environment.
    """
    test = CustomResumeHandler()

    test.generate_custom_resume("Dk", "otter_web", job_description)



