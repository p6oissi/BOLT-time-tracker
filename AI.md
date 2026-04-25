# AI Usage Documentation

---

- **AI used:** Claude Code (Anthropic)
- **Version:** Sonnet 4.6, with high effort

---

## Project Setup

The idea came from a real problem. 
During previous school projects and my ongoing internship, I had to log time manually into a Google spreadsheet. 
When I saw the task brief, I knew I could build something that would make that easier.

I opened Claude Code in **Planning Mode** and entered the following prompt

### Initial prompt
```
I have this task @projectDescription , and I need your help to think this through, help me think about a realistic and 
solid plan and help me execute it later based on the plan. I do not have many ideas, but what I have is that, during my 
studies, I have had a lot of team projects and during them, the coaches want us to track our time manually and then write
it down in a Google sheet, which is kind of stupid, boring and very old school, and I have heard that it is also used in
some IT companies. What I thought would be a nice way to track the time and tasks done, would be an AI bot, living locally
on your device (pc, laptop, whatever you work on), having initially 0 connection with outside servers, for privacy and 
logging purposes. Then, when you start working, you activate the bot manually, or it enables itself automatically (let's 
say when PyCharm or whatever is opened) and it starts to track your time. Now where the functionality comes in is that 
when it is activated and tracks the time, it somehow (screen recording / keylogger / other image or text recognition tool) 
understands what work you do, what applications you open, and all other stuff for your work. It should also understand what
work is connected and when a new task is initialized (could be connected with GitHub / gitlab / jira / etc. for this for example).
This way, developers only need to start working and the logging would happen automatically in the background. What do you 
think about the plan? Would it be realistic to implement within 4 hours and what tools and technologies should I use? For 
code, I would like to use Python, the application should follow all the best practices like SOLID, DRY, KISS, REST API 
principles, validation, clean readable code (not overcomplicated and engineered but simple and stupid without duplication)
with strong, easy to understand and clean comments and documentation where needed. Make sure to tackle this project as a 
group of senior developers / designer / engineers, make small but strong tests to verify code quality and functionality.
As the project only needs to be a prototype, focus only on 1-3 real functionalities that can be tested together, in a logical
flow that it would still make a complete application. It would be also nice to containerize the solution so it would be 
easier to run it if needed. If you have any questions, ideas, remarks, etc., make sure to ask them before starting planning.
Make sure to initialize the project properly and make best use of claude.md principles (add in every dir and sub dir, with
the most important rules and knowledge of the project so that we can follow them while implementation). Make sure the plan
is logically structured and organized, and it is executed step by step, and end with creating a nice, short, easy to read
and descriptive README.md file with the most important info and running steps of the project.
```