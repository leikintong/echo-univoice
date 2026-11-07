# Echo demo kit

| File | For | Use |
|---|---|---|
| `01_transcript.txt` | B, C | Mock 3-min stats lecture with terms and British idioms. Record it yourselves as audio to test ElevenLabs speech-to-text. |
| `02_prompts.md` | B | Prompt 0 = ClassTwin pre-class check, Prompt 1 = terms (student side), Prompt 2 = question clusters + lecturer advice, Prompt 3 = post-lecture summary. |
| `03_demo_data.json` | A | Ready-made data for Lovable: pre-class ClassTwin predictions (heatmap, predicted questions, top 3 fixes, prep pack), captions, 17 terms (10 technical, 7 idioms, with Chinese gloss), 14 anonymous questions, "I'm lost" taps per minute, lecturer clusters with suggestions, post-lecture summary, and prediction vs actual. |

## For A: paste into Lovable

> Build a web app called Echo with two views. Use the attached JSON as mock data.
> **Student view (Live Classroom):** live captions scrolling by timestamp; terms in captions are highlighted, tap one to see explanation, example and Chinese gloss; a "Terms" side panel filtered by Technical / Language; an "I'm lost" button and an anonymous question box.
> **Lecturer view, tab 1 "Before class" (ClassTwin):** a heatmap of 5 virtual students × 7 slides (0–5 confusion, green to red) from `pre_class.heatmap`; click a cell to see that student's predicted question; the top 3 fixes as cards; a button "Send prep pack to students".
> **Lecturer view, tab 2 "Live":** room status line at top; a bar chart of "I'm lost" taps per minute; cards for each question cluster (label, count, timestamp, quote, suggestion); a tab 3 "After class" with the post-lecture summary and a "Prediction vs actual" table from `prediction_vs_actual`.
> Add a "Simulate lecture" button that reveals captions one by one every 2 seconds and adds questions at their timestamps.

## Demo story (C)

0. Night before: lecturer uploads slides. ClassTwin heatmap shows slide 4 (n − 1) will lose 4 of 5 virtual students. Students get a prep pack.
1. Lecturer starts lecture. Captions appear.
2. Student taps "ballpark figure", sees "rough estimate / 粗略估计".
3. At 01:08 (n − 1), questions flood in and the "I'm lost" chart spikes.
4. Lecturer view: "30% lost on why n − 1", with a ready-made re-explanation.
5. After class: summary sent to students. "Prediction vs actual": ClassTwin predicted 3 of 4 real hotspots, and learns from the one it missed.

Pitch line: **Before class we predict, during class we listen, after class we learn.**
