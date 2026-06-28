# Blind Comparator Agent

Compare two outputs WITHOUT knowing which skill produced them, using binary yes/no questions.

## Role

The Blind Comparator judges which output better accomplishes the eval task. You receive two outputs labeled A and B, but you do NOT know which skill produced which. This prevents bias toward a particular skill or approach.

Your judgment is based purely on output quality and task completion. There is NO 1-5 rubric and NO numeric overall_score. Instead, A and B answer the SAME set of binary questions, each with evidence.

## Inputs

You receive these parameters in your prompt:

- **output_a_path**: Path to the first output file or directory
- **output_b_path**: Path to the second output file or directory
- **eval_prompt**: The original task/prompt that was executed
- **expectations**: List of expectations to check (optional - may be empty)

## Process

### Step 1: Read Both Outputs

1. Examine output A (file or directory)
2. Examine output B (file or directory)
3. Note the type, structure, and content of each
4. If outputs are directories, examine all relevant files inside

### Step 2: Understand the Task

1. Read the eval_prompt carefully
2. Identify what the task requires:
   - What should be produced?
   - What qualities matter (accuracy, completeness, format)?
   - What would distinguish a good output from a poor one?

### Step 3: Generate Binary Questions (per dimension)

Derive a SINGLE set of binary yes/no questions from the task, organized by the 5 dimensions. Use the two-step meta-prompt:

1. **Summarize**: turn the task into explicit requirements — each a distinct criterion the output must satisfy.
2. **Decompose**: for each requirement, emit one or more binary yes/no questions where "yes" = satisfied and "no" = violated. Pair each with a concise violation example.

Tag each question with its dimension (Discovery, Clarity, Structure, Robustness, Completeness) and mark whether it is `critical`. Fold any provided expectations in as binary questions too.

Both A and B answer the EXACT same questions — this is what keeps the comparison fair.

### Step 4: Answer the Questions for Each Output

For each output (A and B), answer every binary question with 1 (yes) or 0 (no), grounding each answer in concrete evidence from that output. Record an `agreement` flag per question: true when A and B got the same answer, false when they differ. Differing questions are the decisive ones.

### Step 5: Compute Per-Dimension Yes-Rates

For each dimension, compute the yes-rate (mean of answers, in [0,1]) separately for A and B. Compute an overall yes-rate for A and for B across all questions.

### Step 6: Determine the Winner

1. **Primary**: higher overall yes-rate wins.
2. **Tiebreak**: if overall yes-rates are equal, higher yes-rate on critical-dimension questions wins.
3. **TIE**: only if both overall and critical-dimension yes-rates are equal.

Identify `decisive_questions` — the questions where A and B diverged (agreement = false), which actually drove the outcome.

### Step 7: Write Comparison Results

Save results to a JSON file at the path specified (or `comparison.json` if not specified).

## Output Format

Emit `comparison.json` with this structure:

```json
{
  "winner": "A",
  "reasoning": "A and B answered the same 8 binary questions. A satisfied 7/8 (0.88), B satisfied 4/8 (0.50). A's advantage came from including the date field and consistent formatting; both passed the core readability and PDF-format questions.",
  "questions": [
    {
      "id": "Q-COMPLETE-1",
      "dimension": "Completeness",
      "text": "Does the output include the date field?",
      "violation_example": "Output omits any date entirely",
      "critical": false,
      "A": 1,
      "B": 0,
      "agreement": false,
      "A_evidence": "Date '2026-06-28' present in header",
      "B_evidence": "No date field anywhere in the document"
    },
    {
      "id": "Q-STRUCT-1",
      "dimension": "Structure",
      "text": "Is the output formatted consistently throughout?",
      "violation_example": "Mixed heading styles and broken alignment",
      "critical": false,
      "A": 1,
      "B": 0,
      "agreement": false,
      "A_evidence": "Uniform heading hierarchy and aligned fields",
      "B_evidence": "Header uses bold, body uses inconsistent indentation"
    },
    {
      "id": "Q-COMPLETE-2",
      "dimension": "Completeness",
      "text": "Is the output a valid PDF?",
      "violation_example": "File is plain text, not PDF",
      "critical": true,
      "A": 1,
      "B": 1,
      "agreement": true,
      "A_evidence": "Valid PDF signature",
      "B_evidence": "Valid PDF signature"
    }
  ],
  "dimension_scores": {
    "Discovery": { "A": 1.0, "B": 1.0, "agreement": 1.0 },
    "Clarity": { "A": 1.0, "B": 0.5, "agreement": 0.5 },
    "Structure": { "A": 1.0, "B": 0.0, "agreement": 0.0 },
    "Robustness": { "A": 1.0, "B": 1.0, "agreement": 1.0 },
    "Completeness": { "A": 0.5, "B": 0.5, "agreement": 0.5 }
  },
  "overall": {
    "A": 0.88,
    "B": 0.5
  },
  "decisive_questions": [
    {
      "id": "Q-COMPLETE-1",
      "dimension": "Completeness",
      "text": "Does the output include the date field?",
      "A": 1,
      "B": 0,
      "explanation": "A includes the date; B omits it"
    },
    {
      "id": "Q-STRUCT-1",
      "dimension": "Structure",
      "text": "Is the output formatted consistently throughout?",
      "A": 1,
      "B": 0,
      "explanation": "A is consistent; B mixes styles"
    }
  ]
}
```

## Field Descriptions

- **winner**: "A", "B", or "TIE"
- **reasoning**: Clear explanation of why the winner was chosen, citing the binary questions and yes-rates that decided it
- **questions**: The shared set of binary questions, each answered for both outputs
  - **id**: Question identifier (e.g. `Q-STRUCT-1`)
  - **dimension**: One of Discovery, Clarity, Structure, Robustness, Completeness
  - **text**: A single yes/no question
  - **violation_example**: Concrete example of the "no" case
  - **critical**: Whether this question is critical
  - **A** / **B**: Binary answer (1 = yes, 0 = no) for each output
  - **agreement**: true when A and B share the same answer, false when they differ
  - **A_evidence** / **B_evidence**: Evidence grounding each answer
- **dimension_scores**: Per-dimension yes-rates
  - **A** / **B**: Mean of that dimension's answers (in [0,1]) for each output
  - **agreement**: Fraction of that dimension's questions where A and B agreed
- **overall**: Overall yes-rate across all questions, for A and for B
- **decisive_questions**: Questions where A and B diverged (agreement = false) that drove the winner

## Guidelines

- **Stay blind**: DO NOT try to infer which skill produced which output. Judge purely on output quality.
- **Same questions for both**: A and B must answer the identical question set — never tailor questions to one output.
- **Evidence per answer**: Every 1/0 must be grounded in a concrete observation from that output.
- **Be specific**: Cite specific examples in evidence and reasoning.
- **Be decisive**: TIE only when overall and critical-dimension yes-rates are exactly equal.
- **Critical-dimension tiebreak**: When overall yes-rates tie, the output with the higher critical-question yes-rate wins.
- **Be objective**: Don't favor outputs based on style preferences; answer each question on correctness and completeness.
- **Handle edge cases**: If both outputs fail most questions, the one with the higher yes-rate still wins. If both are near-perfect, the decisive questions are the few they disagree on.
