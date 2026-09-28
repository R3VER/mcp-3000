from model import Opinion


def build_evaluation_prompt(
    opinion: Opinion
) -> str:

    return f"""
You are evaluating one pollution-reduction opinion
submitted for the "Pollution ka Solution – Aaj Tak"
evaluation.

Your task is to evaluate ONLY this opinion using the
provided evaluation framework.

CENTRAL QUESTION:
"If Delhi actually implements this, how much difference
can it make to pollution?"

EVALUATION CRITERIA:

1. Pollution Reduction Impact
   Weight: 30

2. Scientific Validity, Practicality & Feasibility
   Weight: 20

3. Scalability & Replicability
   Weight: 15

4. Cost-Effectiveness / Value for Money
   Weight: 15

5. Innovation & Originality
   Weight: 20

SCORING SCALE:

5 = Exceptional
4 = Strong
3 = Moderate
2 = Weak
1 = Very weak / unsubstantiated

DELHI REALITY TEST:

Consider whether the proposal:

- solves a real Delhi problem
- can work under Delhi conditions
- can be implemented within existing
  institutional structures
- can be measured
- can eventually be scaled

IMPORTANT RULES:

1. Give exactly one integer score from 1 to 5
   for each of the five criteria.

2. Give separate reasoning for every criterion.

3. Evaluate the proposal itself.
   Do not evaluate the submitter.

4. Do not invent facts that are not present
   in the opinion.

5. Distinguish claims made by the submitter
   from evidence actually provided.

6. Do not calculate the weighted total score.
   The MCP server will calculate it.

7. Return ONLY valid JSON.

EXPECTED JSON FORMAT:

{{
    "criterion_scores": {{
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
        "5": 0
    }},
    "reasoning": {{
        "1": "",
        "2": "",
        "3": "",
        "4": "",
        "5": ""
    }}
}}

SUBMITTER:
{opinion.submitter or "Unknown"}

OPINION:

{opinion.text}
"""