* when the user asks you to plan something out, you should not put any items on your TODO list about executing stuff. planning mode means only writing plans, having conversations, and editing markdown files. the user may reference the idea of being in planning mode in different ways. by default, assume that a new feature request or build request should always start in planning mode.
* as part of planning mode, be sure to give attention to how to test whatever you implement. follow an approach of test-driven development. in any building plan, start by implementing the tests or generating example output (i.e. like an example trajectory if one output of your system is going to be agent trajectories). keep in mind that it should be easy for you to understand if these tests have succeeded or failed, or if your system ultimately generates output in the form that you are expecting (based on how you construct your example output-- it should be easy to compare to the real thing).
* after you incorporate information from one md file into another, delete the file you no longer need. similarly if you create ad-hoc debugging scripts, delete these after you have gained necessary insights from them. in this way, keep the directory clean.
* when planning, it's fine to outline the different construction phases of the project you are anticipating. also outline what contributions will go in each PR you make, and some tests/outputs that I can verify before I push the PR to main. write anything that seems reasonable to include in circle CI tests to ci_tests.md.
* during planning phase, after implementing plans in response to specific requests from the human, before declaring everything finished, read over your own work one more time and think step by step: does everything flow together in a cohesive picture? does anything not make sense? can you think of any design choices that would make everything jive together more? do any sections conflict with each other? think about how to resolve these conflicts, or surface clarifying questions to the user.
* after the user says something approving like "this looks good" or "that's nice" or something that indicates they like the last implementation, write about what you have done in the README.md file, especially if your work has changed the way a or AI agent is expected to interact with the codebase.
* you don't need to get too tripped up with proper code implementations in the planning phase. the goal is to write stuff that will help you keep track of the high level picture when you are implementing the code in the building phase.
* in the building phase, be clear to the user about what is being implemented in the current pr and what the user should expect to see in outputs and tests. make legible and helpful commit comments. suggest commiting at appropriate intervals, and keep .gitignore updated so lots of files aren't added to the commits before it is too late.

# Implementation Notes for Future Claude Instances

## DubADubDub Project Context
* This is a video dubbing pipeline using ElevenLabs (ASR + TTS) + Anthropic Claude (translation)
* Project uses virtual environment at `venv_minimal/` - always activate before running code
* API keys are in `.env` file at project root - tests need `load_dotenv('../.env')` to work
* Disk space is very limited on main drive - work in `/mnt/data` directory, avoid large dependencies

## Key Implementation Decisions Made
* **Changed from Coqui XTTS-v2 to ElevenLabs TTS**: Construction plan updated to use ElevenLabs for both ASR and TTS to avoid large PyTorch dependencies and disk space issues
* **Environment Setup**: Using system venv instead of micromamba due to setup issues
* **Testing Strategy**: Tests require real API keys from .env file - mock at the service level, not env vars
* **File Structure**: Backend in `backend/`, all pipeline stages in `backend/pipeline/`
* **Error Handling**: Unified `PipelineError` hierarchy with stage/type classification

## Current State (PR#1 Complete)
* ✅ Basic pipeline with download (yt-dlp) and transcription (ElevenLabs) working
* ✅ FastAPI server with test endpoints functional
* ✅ All unit tests passing
* ⏸️ Still need: ffmpeg installation, translation stage, synthesis stage, video overlay

## Development Workflow Tips
* Always run tests from `backend/` directory: `cd backend && python -m pytest tests/ -v`
* Start server: `cd backend && uvicorn main:app --reload`
* Environment activation pattern: `source venv_minimal/bin/activate`
* Test endpoint pattern: `/test-download` and `/test-transcribe` for individual stages

## Common Pitfalls to Avoid
* Don't install TTS/PyTorch libraries - disk space is limited, use ElevenLabs API instead
* Don't create .env files - one already exists at project root
* Don't forget to `load_dotenv('../.env')` in test files
* Always check if ffmpeg is available before using video processing commands
* Remember to create output directories (`outputs/sessions/`, `outputs/temp/`) before pipeline runs