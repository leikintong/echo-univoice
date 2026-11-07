import pymupdf as fitz
slides = [
 "Lecture 3: Measuring Spread. Today: why the average is not enough.",
 "Two classes both average 65%. Class A scores 60-70, Class B scores 20-100. Same mean, very different spread.",
 "Range = max - min. Quick, a ballpark figure, but sensitive to outliers.",
 "Sample variance: s^2 = sum (x_i - x_bar)^2 / (n-1). We divide by n-1, not n.",
 "Standard deviation s = sqrt(s^2). Same units as the data, so easier to interpret.",
 "As covered in the MLE lecture, the n-1 correction makes the estimator unbiased. This is a rule of thumb you should always apply when working with samples drawn from a population of unknown variance, regardless of the size of the sample or its distribution, as is standard practice in inferential statistics and in every statistical package you will encounter.",
 "Example: scores 4, 6, 8. Mean = 6. Deviations -2, 0, 2. s^2 = 8/2 = 4, s = 2.",
 "Summary: mean tells you the centre; variance and SD tell you the spread.",
]
doc = fitz.open()
for s in slides:
    p = doc.new_page(width=720, height=405)
    p.insert_textbox(fitz.Rect(40, 40, 680, 380), s, fontsize=20)
doc.save("sample_lecture.pdf")
