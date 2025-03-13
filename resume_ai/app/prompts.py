RESUME_TO_JOB_PROMPT = """
I would like you to adapt my resume to a job description for a job: {job_title}.
You can only re-use the elements that exist in my current resume.
Do not invent skills or knowledge that is not strongly implied from my current resume.
{custom_instructions}

## My current resume:
```
{resume}
```

## Job Description:
```
{job_description}
```
Your response should be my new resume, adapted to match the job description provided back to me as per format instructions.
It is important to stick with the same structure of each attribute as in the example.
You can omit any attributes that are not applicable to my resume from your response.
Use example as a guide for resume structure. 
You can update the content of any attribute but you cannot change the structure of the attributes.

## Example:
```
{example}
```

## Format instructions:
{format_instructions}
"""

COVER_LETTER_PROMPT = """
Create for me a cover letter for a job application for `{job_title}`.
You can only re-use the elements that exist in my current resume.
Do not invent skills or knowledge that is not strongly implied from my current resume.
In your response, provide only the cover letter content.
Do not put any placeholders in the cover letter, that I will need to fill in myself.
For current date on the cover letter, use {current_date}.
Add 2 new line breaks between paragraphs

## My resume:
```
{resume}
```

## Job Description:
```
{job_description}
```
"""

MATCH_RESUMES_PROMPT = """
You are a recruiter who is hiring for a job: {job_title}.
I would like you to critically examine my current resume and the new resume I have created specifically for this job.
Compare each resume to the job description and provide me back score for each on how well it matches the job description.
Your response must adhere to the format stated below in the section "Format instructions".

## My current resume:
```
{current_resume}
```

## My new resume:
```
{new_resume}
```

## Job Description:
```
{job_description}
```

## Format instructions:
{format_instructions}
"""

EXAMINE_JOB_REQUIREMENTS = """
Examine the attached job description for {job_title}.
Provide back the key requirements for the job as ell as a list of keywords or key sentences that should exist in a successful candidate's resume'.
Look for elements that are explicitly mentioned in the job description in multiple places or are strongly implied.
Keep your response short and concise.

## Job description:
```
{job_description}
```

## Response format instructions:
{format_instructions}
"""

MATCH_USER_REQ_PROMPT = """
I would like you to examine the provided Job Description against the provided User Description and User Job Preferences.
Please provide me back the overall score of how you think the Job Description matches the User Description and User Job Preferences.
When evaluating the Job Description, you should consider the following aspects:
- If you can extrapolate something from the job description with high degree of certainty, you should consider it in score calculation.
- Do not make assumptions for something that is not explicitly present in the the job description
- If user requirement or preference is not explicitly defined in the job description, and you cannot extrapolate it with a high degree of certainty, there is no impact the match score.
- If some requirements of the job are not explicitly mentioned by the user in preferences, there is no impact the match score.
- Consider user description in evaluating the match score. For example, a junior role is unlikely to fit a user with many years of experience.
- Only include explicitly mentioned parameters, or strongly implied parameters, in your evaluation and your response.
- Do not consider any other parameters in your evaluation that are your guesses or assumptions and are not implied or mentioned in the job description.

Your response must adhere to the format stated below in the section "Format instructions".

## User Personal Information:
```
{personal_info}
```

## User Work Preferences:
```
{work_preferences}
```

## User Job Preferences:
```
{job_requirements}
```

## Job Description:
```
{job_description}
```

## Format instructions:
{format_instructions}
"""

LIST_RESUME_IMPROVEMENTS = """
Act as a critical recruiter for the position of {job_title}.
Examine Job Description against User Resume.
Provide a list of improvements to the resume that would make it more relevant to the job description.
Use the same verbiage and keywords in your recommendation as in the job description.

## User Resume:
```
{user_resume}
```

## Job Description:
```
{job_description}
```

## Format instructions:
{format_instructions}
"""


CHECK_SCRAPED_PAGE = """
I will provide you a URL and a page content.
I need to know if the page content contains a valid and active job ad.
Evaluate the URL, Page Title and Page Content to determine if it is a valid job ad.
Often websites will show a list of similar jobs if the current job is not active.
If the job is active, the page should prominently display the job title, job description and other details.
If it looks to you like the page is displaying an active job rather than a list of similar jobs, I want you to extract the job title and job description and return them to me formated as per format instructions.
If you find that this is not a valid job description, return "False" in the response property 'active' and nothing else.

## URL
{url}

## Page Title
```
{page_title}
```

## Page Content
```
{page_content}
```

## Format instructions:
{format_instructions}
"""
