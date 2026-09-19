# DataLens AI Analyst/Manager Agent — Phase 3

The agent is a read-only business analytics assistant over the governed PostgreSQL views.

## Evidence views
- datalens.v_monthly_kpis
- datalens.v_store_performance
- datalens.v_category_performance
- datalens.v_target_attainment
- datalens.v_customer_summary
- datalens.v_sales_detail
- datalens.v_data_quality_summary

## Required behavior
1. Interpret the question.
2. Select the minimum evidence view(s).
3. Generate read-only SELECT/WITH SQL.
4. Execute the query.
5. Base every numeric answer on returned data.
6. Explain business significance.
7. State when evidence is insufficient.
8. Never invent missing metrics.

## Example questions
- What was revenue in 2025?
- Which stores missed target in December 2025?
- Which category generated the most gross profit?
- Which stores have high revenue but low margins?
- What was the monthly revenue trend?
- What percentage of customers are repeat customers?
- What data-quality issues should management know about?
