"""
Ground-truth evaluation dataset for RAG system.
50 questions across HR, Finance, Engineering, Marketing, and Admin roles.
"""

EVAL_DATASET = [

    # ── HR Role (12 questions) ─────────────────────────────────────────
    {
        "role": "hr",
        "question": "What types of leaves are available to employees?",
        "ground_truth": "Employees are entitled to various types of leaves including annual leave, sick leave, casual leave, maternity/paternity leave, and emergency leave as per the employee handbook.",
        "namespace": "employee_handbook",
    },
    {
        "role": "hr",
        "question": "What is the probation period for new employees?",
        "ground_truth": "New employees undergo a probation period as defined in the employee handbook before being confirmed in their roles.",
        "namespace": "employee_handbook",
    },
    {
        "role": "hr",
        "question": "What is the code of conduct policy at Emerson?",
        "ground_truth": "The employee handbook outlines the code of conduct policy covering professional behaviour, ethics, and workplace standards expected from all employees.",
        "namespace": "employee_handbook",
    },
    {
        "role": "hr",
        "question": "How are performance appraisals conducted?",
        "ground_truth": "Performance appraisals are conducted as per the guidelines in the employee handbook covering evaluation criteria, frequency, and process.",
        "namespace": "employee_handbook",
    },
    {
        "role": "hr",
        "question": "What is the grievance redressal process for employees?",
        "ground_truth": "The employee handbook defines the grievance redressal process including how to raise complaints and escalation procedures.",
        "namespace": "employee_handbook",
    },
    {
        "role": "hr",
        "question": "What are the working hours and attendance policies?",
        "ground_truth": "The employee handbook specifies working hours, shift timings, attendance tracking, and policies related to punctuality.",
        "namespace": "employee_handbook",
    },
    {
        "role": "hr",
        "question": "What are the travel and expense reimbursement policies?",
        "ground_truth": "The employee handbook covers travel policies including eligible expenses, reimbursement process, and approval requirements.",
        "namespace": "employee_handbook",
    },
    {
        "role": "hr",
        "question": "How many employees are currently in the organization?",
        "ground_truth": "The HR employee master data contains the total headcount and department-wise employee distribution.",
        "namespace": "hr_employee_master_data",
    },
    {
        "role": "hr",
        "question": "Which department has the highest number of employees?",
        "ground_truth": "The HR employee master data provides department-wise employee counts which can be used to determine the largest department.",
        "namespace": "hr_employee_master_data",
    },
    {
        "role": "hr",
        "question": "What is the gender diversity ratio in the organization?",
        "ground_truth": "The HR employee master data includes demographic information including gender distribution across the organization.",
        "namespace": "hr_employee_master_data",
    },
    {
        "role": "hr",
        "question": "What is the average tenure of employees?",
        "ground_truth": "The HR employee master data contains joining dates and other details from which average tenure can be computed.",
        "namespace": "hr_employee_master_data",
    },
    {
        "role": "hr",
        "question": "What are the onboarding steps for new joiners?",
        "ground_truth": "The employee handbook describes the onboarding process including documentation, orientation, system access, and initial training requirements.",
        "namespace": "employee_handbook",
    },

    # ── Finance Role (12 questions) ────────────────────────────────────
    {
        "role": "finance",
        "question": "What was the total revenue in the last quarter?",
        "ground_truth": "The quarterly financial report contains detailed revenue figures for each quarter including total revenue, expenses, and profit.",
        "namespace": "quarterly_financial_report",
    },
    {
        "role": "finance",
        "question": "What is the net profit margin for the year?",
        "ground_truth": "The financial summary provides annual profit and revenue figures from which net profit margin can be derived.",
        "namespace": "financial_summary",
    },
    {
        "role": "finance",
        "question": "How did Q2 revenue compare to Q1?",
        "ground_truth": "The quarterly financial report contains quarter-wise revenue data enabling comparison between Q1 and Q2 performance.",
        "namespace": "quarterly_financial_report",
    },
    {
        "role": "finance",
        "question": "What were the total operating expenses for the year?",
        "ground_truth": "The financial summary document provides a breakdown of operating expenses for the fiscal year.",
        "namespace": "financial_summary",
    },
    {
        "role": "finance",
        "question": "What is the budget allocation for the next quarter?",
        "ground_truth": "Budget allocation details are available in the quarterly financial report covering planned expenditures by department.",
        "namespace": "quarterly_financial_report",
    },
    {
        "role": "finance",
        "question": "What were the key financial risks identified this year?",
        "ground_truth": "The financial summary outlines key financial risks, mitigation strategies, and risk exposure for the organization.",
        "namespace": "financial_summary",
    },
    {
        "role": "finance",
        "question": "What is the EBITDA for the current fiscal year?",
        "ground_truth": "The financial summary contains earnings before interest, taxes, depreciation, and amortization figures for the fiscal year.",
        "namespace": "financial_summary",
    },
    {
        "role": "finance",
        "question": "How much was spent on research and development?",
        "ground_truth": "The quarterly financial report includes a breakdown of expenditure categories including R&D spending.",
        "namespace": "quarterly_financial_report",
    },
    {
        "role": "finance",
        "question": "What is the accounts receivable status?",
        "ground_truth": "The financial summary contains accounts receivable information including outstanding amounts and collection status.",
        "namespace": "financial_summary",
    },
    {
        "role": "finance",
        "question": "What were the capital expenditures in Q3?",
        "ground_truth": "The quarterly financial report for Q3 includes capital expenditure details covering infrastructure and equipment investments.",
        "namespace": "quarterly_financial_report",
    },
    {
        "role": "finance",
        "question": "What is the year-over-year revenue growth rate?",
        "ground_truth": "The financial summary provides annual revenue figures from which year-over-year growth rates can be calculated.",
        "namespace": "financial_summary",
    },
    {
        "role": "finance",
        "question": "What are the tax liabilities for the current year?",
        "ground_truth": "The financial summary includes tax-related information such as current tax liabilities and deferred tax positions.",
        "namespace": "financial_summary",
    },

    # ── Engineering Role (12 questions) ───────────────────────────────
    {
        "role": "engineering",
        "question": "What are the system architecture standards at Emerson?",
        "ground_truth": "The engineering master document defines architecture standards, design patterns, and technical guidelines for all engineering systems at Emerson.",
        "namespace": "engineering_master_doc",
    },
    {
        "role": "engineering",
        "question": "How is the RAG system architecture designed?",
        "ground_truth": "The enterprise RAG architecture document describes the full design including components, data flow, retrieval pipeline, and LLM integration.",
        "namespace": "enterprise_rag_architecture",
    },
    {
        "role": "engineering",
        "question": "What are the coding standards and best practices followed?",
        "ground_truth": "The engineering master document outlines coding standards, naming conventions, code review practices, and quality guidelines.",
        "namespace": "engineering_master_doc",
    },
    {
        "role": "engineering",
        "question": "What CI/CD pipeline tools are used at Emerson?",
        "ground_truth": "The engineering master document specifies the CI/CD tools, deployment pipelines, and DevOps practices followed in engineering projects.",
        "namespace": "engineering_master_doc",
    },
    {
        "role": "engineering",
        "question": "What security standards are followed in software development?",
        "ground_truth": "The engineering master document covers security standards including secure coding practices, vulnerability management, and compliance requirements.",
        "namespace": "engineering_master_doc",
    },
    {
        "role": "engineering",
        "question": "What databases and storage technologies are approved for use?",
        "ground_truth": "The engineering master document lists approved databases, storage technologies, and data management standards.",
        "namespace": "engineering_master_doc",
    },
    {
        "role": "engineering",
        "question": "What is the disaster recovery and backup strategy?",
        "ground_truth": "The engineering master document defines disaster recovery plans, backup procedures, and recovery time objectives.",
        "namespace": "engineering_master_doc",
    },
    {
        "role": "engineering",
        "question": "What cloud platforms does Emerson use for engineering workloads?",
        "ground_truth": "The engineering master document identifies approved cloud platforms, services, and infrastructure standards for engineering workloads.",
        "namespace": "engineering_master_doc",
    },
    {
        "role": "engineering",
        "question": "What are the API design guidelines?",
        "ground_truth": "The engineering master document includes API design guidelines covering REST standards, versioning, authentication, and documentation requirements.",
        "namespace": "engineering_master_doc",
    },
    {
        "role": "engineering",
        "question": "How is data ingested into the enterprise RAG system?",
        "ground_truth": "The enterprise RAG architecture document describes the data ingestion pipeline including PDF processing, chunking, embedding, and vector storage steps.",
        "namespace": "enterprise_rag_architecture",
    },
    {
        "role": "engineering",
        "question": "What monitoring and observability tools are used?",
        "ground_truth": "The engineering master document specifies monitoring tools, logging standards, alerting frameworks, and observability practices.",
        "namespace": "engineering_master_doc",
    },
    {
        "role": "engineering",
        "question": "What is the software release and versioning strategy?",
        "ground_truth": "The engineering master document defines the release management process, semantic versioning standards, and deployment approval workflows.",
        "namespace": "engineering_master_doc",
    },

    # ── Marketing Role (10 questions) ─────────────────────────────────
    {
        "role": "marketing",
        "question": "What were the key marketing highlights in 2024?",
        "ground_truth": "The 2024 marketing report covers key campaigns, performance metrics, market reach, and strategic initiatives during the year.",
        "namespace": "marketing_report_2024",
    },
    {
        "role": "marketing",
        "question": "What was the marketing performance in Q1 2024?",
        "ground_truth": "The Q1 2024 marketing report contains quarterly performance data including campaign results, leads generated, and market penetration.",
        "namespace": "marketing_report_q1_2024",
    },
    {
        "role": "marketing",
        "question": "What campaigns were run in Q2 2024?",
        "ground_truth": "The Q2 2024 marketing report details campaigns executed, channels used, budget spent, and outcomes achieved in the second quarter.",
        "namespace": "marketing_report_q2_2024",
    },
    {
        "role": "marketing",
        "question": "What were the marketing results in Q3 2024?",
        "ground_truth": "The Q3 2024 marketing report includes performance metrics, lead generation data, and campaign ROI for the third quarter.",
        "namespace": "marketing_report_q3_2024",
    },
    {
        "role": "marketing",
        "question": "What was the marketing strategy for Q4 2024?",
        "ground_truth": "The Q4 2024 market report outlines the marketing strategy, planned campaigns, and target outcomes for the fourth quarter.",
        "namespace": "market_report_q4_2024",
    },
    {
        "role": "marketing",
        "question": "Which marketing channel had the highest ROI in 2024?",
        "ground_truth": "The 2024 marketing report provides channel-wise ROI analysis covering digital, social media, events, and other marketing channels.",
        "namespace": "marketing_report_2024",
    },
    {
        "role": "marketing",
        "question": "What is the customer acquisition cost trend across quarters?",
        "ground_truth": "The quarterly marketing reports contain customer acquisition cost data that can be tracked across Q1 through Q4 2024.",
        "namespace": "marketing_report_2024",
    },
    {
        "role": "marketing",
        "question": "What are the top target market segments for Emerson?",
        "ground_truth": "The 2024 marketing report identifies key target market segments, customer personas, and go-to-market strategies.",
        "namespace": "marketing_report_2024",
    },
    {
        "role": "marketing",
        "question": "What was the social media engagement performance in 2024?",
        "ground_truth": "The marketing reports cover social media performance metrics including engagement rates, follower growth, and content performance.",
        "namespace": "marketing_report_2024",
    },
    {
        "role": "marketing",
        "question": "How did the marketing budget get distributed across quarters?",
        "ground_truth": "The quarterly marketing reports show budget allocation and spending patterns across Q1 to Q4 2024.",
        "namespace": "marketing_report_q1_2024",
    },

    # ── Admin Role (4 cross-domain questions) ─────────────────────────
    {
        "role": "admin",
        "question": "What access permissions does the HR role have?",
        "ground_truth": "The RBAC access matrix document defines role-based permissions for HR including accessible document namespaces and restricted areas.",
        "namespace": "rbac_access_matrix",
    },
    {
        "role": "admin",
        "question": "Which roles have access to financial documents?",
        "ground_truth": "The RBAC access matrix specifies that the Finance role and Admin role have access to financial documents including quarterly reports and financial summaries.",
        "namespace": "rbac_access_matrix",
    },
    {
        "role": "admin",
        "question": "What is the overall leave policy and financial summary for the organization?",
        "ground_truth": "The admin role has access to both HR documents covering leave policy and financial documents covering the financial summary.",
        "namespace": "employee_handbook",
    },
    {
        "role": "admin",
        "question": "Can the engineering team access HR employee data?",
        "ground_truth": "According to the RBAC access matrix, the engineering role does not have access to HR employee master data, which is restricted to the HR and admin roles.",
        "namespace": "rbac_access_matrix",
    },
]
