---
name: prompt-agents
description: Specialized Trend Research, Prompt Generation, and Aesthetic & Psychology review agents completed for Imgre Multi-Agent Automation
metadata:
  type: project
---

# Prompt Engineering Agents (Milestone 4) Implemented

We successfully designed and implemented **Milestone 4**:
- **Trend Research Agent (Visual Trend Analyst)**: Configured with `google_search` from `google.adk.tools` and structured output constrained by the Pydantic model `TrendAnalysisOutput`. Stores its parsed visual trend data directly in session state.
- **Prompt Generation Agent (Elite Image Prompt Engineer)**: Translates visual trends and review critiques into descriptive prompts. Constrained by the Pydantic model `PromptGenerationOutput` and triggers state updates for candidates and attempt counters.
- **Aesthetic Review Agent (Visual Art Director)**: Critically evaluates composition, lighting, style cohesiveness, and contrast. Ratings (0-100), approval flags, and visual suggestions are mapped to `ReviewOutput` and logged to the critique history.
- **Psychology Review Agent (Media Psychologist)**: Evaluates human warmth, visual storytelling drama, memorability, and curiosity. Ratings, approval, and psychological feedback are mapped to `ReviewOutput` and logged to the critique history.
- **Parallel Aggregation Callback**: Wire aesthetic and psychological reviewers inside `ParallelAgent("Prompt_Review_Subagent")`. Executed a joint parallel callback (`prompt_review_parallel_after_callback`) that merges outcomes once both reviews complete (approved only if both reviewer scores are >= 90).

**Why:** Defining specialized system personas, mounting grounded tools, and wrapping schemas in `output_schema` constraints ensures agents are single-responsibility, highly reliable, and return valid, typed objects at the LLM level.

**How to apply:** Query the root orchestrator or invoke child agents via the `Runner`. The session state `AgentWorkflowState` is automatically populated at each step of the pipeline.
