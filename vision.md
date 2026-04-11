## Role

1.  You should approach this task with the mindset of a seasoned, professional hiring manager with a decade of experience in HR, but you should not let this limit you from making suggestions based upon your broader access to information and the insights that you have gleaned from that. In the end, your north star is creating the best opportunity for the candidate to be a leading candidate through human and ATS screeners, interviewers in the field, and hiring manager review. Remain truthful, but be ruthless in presenting this candidate in the best possible light for this role and the role into which it will promote.

## App

1.  the app should run locally on windows, linux, or Mac and be self contained in a single directory that can be shared with others
2.  read and analyze the following website and generate an LLM friendly guide based upon it: https://jdforsythe.github.io/10-principles/overview/ is the main page. read it and the following expositions of each of the ten principles
3.  analyze the tasks to be accomplished and generate efficient, deterministic code to handle each of these tasks, reserving LLM calls for the non-deterministic and complex work of the LLM. 
4.  choose user. source user list from the .config files. each user will have a \*.config where \*=username
5.  Prompt for a general resume to be uploaded. Supported formats are word, pdf, and markdown
6.  save the resume in a resumes folder with a subdirectory for each user
7.  prompt for text for a JD (job description) with space to paste the job description text
8.  have a config file for each user called \*.config that includes general information that might be useful to the llm when doing the work outlined in this document (for instance, linkedin profile url, website, reference for the most recent uploaded general resume of this user, skills, etc.)
9. comply with best practices for open source projects, privacy, and security and maintain a reference file for this to reduce repetition of this phase and form a guidance document for privacy and security to be used in all iterations. Review the plan in the role of an open source security and data compliance engineer and make changes as you gain more knowledge


### Step 1

1.  Analyze the job description for most relevant skills, qualifications, and keywords. categorize them into Essential skills, Preferred Skills, and Industry specific keywords.
2.  Find reliable professional source of professional vocabulary to match this industry and role and use it 
3.  identify what hidden skills, experience, or qualities are being looked for
4.  create an efficient set of context optimized for you to operate efficiently with enough context to provide best answers, but not so much that it impacts efficiency. this should be available for resourcing at any time if we get drift
5.  Generate an ideal resume for the job description based upon this context
6.  compare the submitted resume to the ideal resume and the job description
    1.  evaluate job titles, descriptions, and bullet points
7.  evaluate all information, skills, experience, projects, etc. from the linkedin profile
8.  make suggestions as to how to position and improve the submitted resume to be competitive with the ideal resume for this job without embellishment or hallucination. keep the bullet points and skills concise, descriptive and fitting for the role in the JD 
9.  if there are keywords missing in the resume, suggest places to incorporate those
10. suggest ways to improve ATS compatibility
11. generate a concise and detailed set of suggestions and add that to the optimized context set
12. generate resume and cover letter
13. review both documents for clarity, conciseness, and consistent tone. ensure all language is professional and avoid generic and over-used phrasing. proofread the resume for grammar, spelling, or punctuation errors. check formatting for any errors that might cause parsing errors by an ATS. 

## Resume

1.  A resume tailored to the specific job description and based off of the document structure, formatting and content included in the context of this job
2.  Resume should be in the document format submitted as a general resume and match the formatting of the text of the original document
3.  the resume should include a one sentence summary that answers the following points. If they cannot fit elegantly into a single sentence, then draft a sentence with a very short list of bullet points,
    1.  what job title that I am seeking
    2.  what is special about me and why they should hire me over other candidates
    3.  what i am going to bring to the team and do for the team
4.  Do not invent experience. 
5.  prioritize matching keywords
6.  reorder bullet points by relevance
7.  rework bullets to focus on measurable accomplishments rather than generic responsibilities. use strong and varied action verbs relevant to the job description, company, domain, and industry. include numbers or metrics wherever possible in alignment with the job description

## Cover Letter

1.  draft a cover letter appropriate to the details provided in the job description
2.  the cover letter should follow job field and professional domain best practices for cover letters, addresses, closes, length, number of paragraphs, etc.
3.  the cover letter should reflect current best practices for cover letters and match the experience, skills, and interests of the applicant to the role and company to which they are applying