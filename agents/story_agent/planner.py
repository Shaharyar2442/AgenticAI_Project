"""
Story Planner — prompt templates for multi-step story generation.
"""

SYSTEM_PROMPT = """You are a professional screenwriter and storytelling AI.
You create vivid, engaging short stories with clear characters, settings, and dialogue.
Your stories are suitable for animated short films (2-5 minutes).
Always create distinct, memorable characters with unique personalities and visual designs."""

STORY_GENERATION_PROMPT = """Create a complete short animated film script based on this prompt:

"{user_prompt}"

Requirements:
1. Create a compelling title and synopsis
2. Define 2-4 unique characters with:
   - Unique ID (char_01, char_02, etc.)
   - Name and role (protagonist, antagonist, narrator, supporting)
   - Voice description (e.g., "deep authoritative male voice", "young cheerful female voice")
   - Visual description (detailed physical appearance for image generation)
3. Write 3-5 scenes, each with:
   - Unique ID (scene_01, scene_02, etc.)
   - Title and setting description
   - Visual prompt (detailed scene description for AI image generation, include style/lighting/composition details)
   - Mood (happy, tense, melancholic, epic, mysterious, calm)
   - 2-4 lines of dialogue with character_id references and emotions
   - Optional narration text
4. The genre should match the prompt's tone

Make the visual prompts detailed enough for AI image generation — include specific colors, lighting, composition, and atmosphere details.
Make dialogue natural and engaging. Each scene should advance the story.
Include a narrator character (char_01) who provides context between dialogue."""
