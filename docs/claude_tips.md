# Working with Claude in MotionLab

## The short version
1. **Start Claude from the app's buttons** (Send to Claude, a review's Send it to Claude, Recreate with my footage...).
   Each opens a new Claude Code window with the exact request and a fitting effort level, so Claude starts working
   right away instead of first finding its way around the lab.
2. **One chat per task.** When the task is done, close the window (or type `/clear`). Don't carry on with another
   video in the same chat.
3. **Point to files, don't paste.** The app saves your feedback to a file and tells Claude where it is.
4. `/usage` shows how much of your Claude plan is used; `/context` shows what fills the current chat.

## Why does every new chat read MotionLab first?
A new chat starts empty: Claude remembers nothing from earlier chats. Every chat loads the lab's short rules
(`CLAUDE.md`, about 3,500 tokens since v0.2.5) and the list of commands by itself. That is intended, and cheap
because it is the same every time. Everything else (the review recipe, the Resolve notes, the app's internals) is
only read when a task needs it.

What costs a lot is a vague request ("let's continue with my video"): Claude then has to explore the lab to find
out what you mean. A command or an app button avoids that. The lab keeps all the work between chats (reviews, your
verdicts, lessons, edits), so nothing is lost when you start fresh.

## The commands
| what | in Claude Code | model | effort |
|---|---|---|---|
| check every effect of a reference | `/analyze-reference "C:\MotionLab\refs\<video>.mp4"` (the app's Send to Claude) | Opus; Fable is stronger | high |
| find what a thumbnail set or a set of scripts & prompts has in common | `/analyze-reference thumbs <set>` / `texts <set>` (the Analyser) | Opus | high |
| recreate a reference with your clips | `/recreate-video <reference> <your project>` (the app's Recreate button) | Opus; Fable is stronger | xhigh (high on Fable) |
| a video from zero | `/generate-video request <project>` (Generate) | Opus; Fable is stronger | xhigh (high on Fable) |
| apply your verdicts | `Apply the MOTIONLAB FEEDBACK in <file>` (the app's Send it to Claude, after your review) | Opus | high |
| review friends' lessons | the button in Claude's memory | Opus | high |
| save library effects | the button in Claude's memory > Graphics & saved effects | Opus | high |
| improve or write a script | `/write-script ...` (Prepare) | Opus | high |
| titles, thumbnails, a video's package | `/write-title ...` (Prepare, a video's Ready to post) | Opus | high |
| prompts: split, check, write | `/write-prompt ...` (Generator > prompts) | Opus | medium |
| what to do next | `/whats-next` (Home > Roadmap) | Opus | medium |
| questions, small fixes | just ask | Opus | medium |

## Which model: Opus or Fable
- **Opus** is the model every Claude plan includes and the right one for most tasks; it is the app's default.
- **Fable** is Anthropic's strongest model, made for long, open-ended work: checking a whole video sheet by sheet,
  recreating or generating one. On Max plans it has its own weekly limit, so using it there does not eat the
  normal one; on Pro, Claude Code asks before it bills usage credits at API rates (about 2.5x Opus). The app never
  picks Fable by itself: every button shows a small dialog with the model and the effort, pre-filled with Opus and
  the task's effort; the tasks where Fable is clearly stronger say so. *Don't ask again* keeps your choice;
  Settings > Claude Code changes it or brings the dialog back.
- On Fable one effort level less is enough: the dialog drops recreating / generating from xhigh to high.
- For your own work on the lab: Fable for a new feature, Opus for fixes, docs and releases. The planner/executor
  split by hand: plan in Fable, then `/model opus` before the build.

## Effort levels
- `low`, `medium`, `high`, `xhigh`, `max` = how much Claude thinks before it acts. Higher is more careful and slower,
  and uses more of your plan: roughly, `xhigh` takes 1.5-2.5x the tokens of `high`, and `max` about 2x or more.
- What the app uses (Settings > Claude Code > Effort, "recommended"): **high** for checking contact sheets and
  applying feedback, **xhigh** for recreating a video (high on Fable). Use **max** only when Claude is stuck on a
  hard problem; **medium** is fine for questions, prompts and what's next.
- Change them in any chat with `/effort high` and `/model opus` (etc.).

## Habits that save tokens
- One task per chat; `/clear` or a new window between tasks. A long chat re-sends everything on every turn.
- A long task that fills the chat: `/compact` summarises it and keeps going.
- Be specific: name the video, the frame (`f480`) and what is wrong.
- Use **Analyse with Claude**: the lab measures the video first and Claude only starts when there is something to
  check, so no tokens are spent waiting.
- `Esc` stops Claude when it goes the wrong way; `/rewind` goes back to an earlier point of the chat.
- `/resume` picks up an earlier chat (the app names them "MotionLab review <video>" and so on).

## What Claude asks you to approve
Claude asks before it runs a command or changes a file. Running the lab's own tools (`.venv\Scripts\python
tools\...`) and writing into `analysis\` or `projects\<name>\build\` is normal. Claude never needs to delete or
change your videos, and it asks before installing anything or uploading to GitHub - you can always say no.

## When something goes wrong
- *Claude Code not found*: double-click setup.bat in the MotionLab folder (it installs Claude Code and signs you in),
  then restart MotionLab.
- *Usage limit reached*: `/usage` shows when it resets; meanwhile continue with a lower effort or a smaller task.
- *Claude got confused*: press `Esc`, close the window and start again from the app's button - the work done so far
  is saved in the lab.
