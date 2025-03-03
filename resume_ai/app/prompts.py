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
Make sure the properties in your response have the same order as in the example.
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

MATCH_USER_REQ_PROMPT = """
You are a recruiter who is hiring for a job: {job_title}.
I would like you to critically examine my current resume and the new resume I have created specifically for this job.
Compare each resume to the job description and provide me back score for each on how well it matches the job description.
Your response must adhere to the format stated below in the section "Format instructions".

## User Description:
```
{user_descr}
```

## User Job Requirements:
```
{user_job_req}
```

## Job Description:
```
{job_description}
```

## Format instructions:
{format_instructions}
"""