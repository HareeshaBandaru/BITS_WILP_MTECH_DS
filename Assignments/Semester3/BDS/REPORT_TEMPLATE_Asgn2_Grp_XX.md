# BIG DATA SYSTEMS – ASSIGNMENT 2
## Amazon Product Review Analysis using Apache Spark

**Report Template for Group Submission**

---

## 1. GROUP INFORMATION

| Attribute | Details |
|-----------|---------|
| **Group Number** | XX |
| **Member 1** | Name: _________________  BITS ID: _________________ |
| **Member 2** | Name: _________________  BITS ID: _________________ |
| **Member 3** | Name: _________________  BITS ID: _________________ |
| **Group Leader** | [Name] |
| **Contribution Distribution** | Member 1: __% | Member 2: __% | Member 3: __% |

---

## 2. DEVELOPMENT ENVIRONMENT & SETUP

### Environment Details
- **Operating System**: [Windows/Mac/Linux]
- **Python Version**: 3.8+
- **Apache Spark Version**: 3.1.0 or higher
- **PySpark Version**: [Version used]
- **Jupyter Notebook Version**: [Version used]
- **IDE/Environment**: [Google Colab/Local Jupyter/DataBricks]

### Setup Steps
1. [Document how Spark was installed and configured]
2. [Dataset location and preparation]
3. [Any dependencies or libraries installed]
4. [Configuration parameters used]

---

## 3. PROBLEM-SOLVING APPROACH

### Methodology
[Describe your approach to solving the assignment, including:]
- Data loading and validation strategy
- Cleansing and preprocessing steps
- Analytical approach for each query
- Optimization strategy used

### Architecture Decisions
[Explain key decisions made during implementation, such as:]
- Why specific Spark operations were chosen
- Partitioning and caching strategies
- SQL vs DataFrame API usage
- Performance optimization choices

---

## 4. QUERY RESULTS & ANALYSIS

### Query (i): Data Loading with Schema Inference

**Code Snippet:**
```python
# Load with schema inference
df_raw = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv(data_path)
```

**Results:**
- Total Records Loaded: [Insert count]
- Total Columns: [Insert count]
- Schema: [Include printSchema() output]

**Observations:**
[Describe what you observed about the data structure]

---

### Query (ii): Data Cleansing and Schema Modification

**Cleansing Actions:**
1. Created `primary_category` column
2. Dropped rows with NULL or invalid ratings
3. [Other cleansing actions]

**Results:**
- Records Before Cleansing: [Insert count]
- Records Dropped: [Insert count]
- Records After Cleansing: [Insert count]
- Data Retention Rate: [Insert %]

**Modified Schema:**
[Include schema output after modification]

---

### Query (iii): Top Products by Average Rating (Minimum 20 Reviews)

**Approach:**
[Explain how you calculated this]

**Top 15 Results:**
[Insert table or screenshot showing results]

**Key Insights:**
- [Insight 1]
- [Insight 2]
- [Insight 3]

---

### Query (iv): Top 10 Most Active Reviewers

**Results Table:**
[Insert top 10 reviewers with review counts and average ratings]

**Analysis:**
[Discuss patterns in reviewer behavior]

---

### Query (v): Monthly Trend of Average Ratings per Category

**Time Period Covered:** [Start date to End date]

**Sample Results (40 rows):**
[Insert table or screenshot]

**Trends Identified:**
- [Trend 1]
- [Trend 2]
- [Category with highest variance]

---

### Query (vi): Top 10 Products by 5-Star to 1-Star Ratio

**Results:**
[Insert table showing product names with ratio calculations]

**Interpretation:**
[Discuss what this ratio tells us about product quality perception]

---

### Query (vii): Longest Review Texts per Category

**Sample Results:**
[Insert table showing longest reviews per category]

**Analysis:**
[Discuss what categories have longest reviews and why]

---

### Query (viii): Year-over-Year Growth in Review Counts

**Results:**
[Insert YoY growth table]

**Growth Analysis:**
- Year with highest growth: [Year] ([Percentage]%)
- Year with lowest growth: [Year] ([Percentage]%)
- Overall trend: [Increasing/Decreasing/Fluctuating]

---

### Query (ix): Average Rating by Review Length Buckets

**Bucket Distribution:**
[Insert table with distribution by length bucket]

**Key Finding:**
[Discussion of correlation between review length and rating]

---

### Query (x): Products with Declining Ratings Over Time

**Top 10 Declining Products:**
[Insert table with rating drops]

**Observation:**
[Comment on scale of declines and affected categories]

---

### Query (xi): Analysis of Product with Maximum Rating Decline

**Selected Product:** [Product name]

**Rating Decline:** [Amount in stars]

**Analysis Summary:**
[Provide data-driven analysis including:]
- Monthly rating trend
- Review volume pattern
- Rating distribution changes
- Possible causes identified

**Findings & Recommendations (Max 150 words):**
[Insert your analysis and recommendations here]

---

### Query (xii): Performance Optimization Analysis

**Identified Bottleneck:**
[Describe which query was optimized and why]

**Optimization Techniques Applied:**
1. [Technique 1]
   - Implementation details
   - Expected benefit
   
2. [Technique 2]
   - Implementation details
   - Expected benefit

**Performance Comparison:**

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|------------|
| Execution Time | [X] seconds | [Y] seconds | [Z]% faster |
| Memory Usage | [X] MB | [Y] MB | [Change]% |
| Shuffle Size | [X] GB | [Y] GB | [Change]% |
| Speedup Factor | 1.0x | [Y]x | - |

**Justification:**
[Explain why the optimization worked and the trade-offs involved]

**Code Comparison:**
```python
# Baseline approach
[Include unoptimized code snippet]

# Optimized approach
[Include optimized code snippet]
```

---

## 5. CONCLUSIONS & INSIGHTS

### Business Insights
1. [Key insight 1]
2. [Key insight 2]
3. [Key insight 3]

### Technical Learnings
1. [Learning 1]
2. [Learning 2]
3. [Learning 3]

### Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]

---

## 6. CHALLENGES & SOLUTIONS

| Challenge | Solution | Outcome |
|-----------|----------|---------|
| [Challenge 1] | [Solution] | [Outcome] |
| [Challenge 2] | [Solution] | [Outcome] |
| [Challenge 3] | [Solution] | [Outcome] |

---

## 7. APPENDIX

### A. Additional Code Snippets
[Include any important code not shown in main sections]

### B. Screenshots
[Include execution screenshots of key results]

### C. References
- Apache Spark Documentation: https://spark.apache.org/docs/latest/
- PySpark SQL Functions: https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql.html
- [Other references used]

---

**Document Prepared By:** [Name]  
**Date:** [Date]  
**Last Updated:** [Date]

---

### NOTES FOR SUBMISSION:
- Replace all placeholders [like this] with actual values
- Include clear tables and formatted code snippets
- Add screenshots of actual execution results
- Ensure professional formatting and readability
- All team members should review and approve before submission
- Save as PDF and DOC (Word) formats
- File naming: `Asgn2_Grp_XX_report.pdf` and `Asgn2_Grp_XX_report.docx`

