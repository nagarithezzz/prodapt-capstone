import re
from collections import Counter

SKILLS_KEYWORDS = [
    # === Programming Languages ===
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "golang",
    "rust", "swift", "kotlin", "scala", "php", "perl", "matlab", "r",
    "html", "css", "sass", "less", "graphql", "assembly", "shell", "bash",
    "powershell", "sql", "nosql", "pl/sql", "t-sql", "vb.net", "delphi",
    "julia", "lua", "haskell", "clojure", "erlang", "elixir", "dart",
    # === Frameworks & Libraries ===
    "react", "react.js", "angular", "angular.js", "vue.js", "vue", "node.js",
    "nodejs", "express.js", "express", "django", "flask", "spring boot",
    "spring", "spring framework", "rails", "ruby on rails", "laravel",
    "asp.net", ".net", ".net framework", ".net core", "tensorflow",
    "pytorch", "keras", "scikit-learn", "pandas", "numpy", "jquery",
    "bootstrap", "tailwind css", "tailwind", "next.js", "nuxt.js", "svelte",
    "fastapi", "redux", "webpack", "jest", "mocha", "cypress", "selenium",
    "playwright", "puppeteer", "three.js", "d3.js", "chart.js",
    "qt", "gtk", "wxwidgets", "opencv", "opengl", "directx", "unity",
    "unreal engine", "godot", "flutter", "react native", "xamarin",
    "electron", "tauri", "wxpython", "tkinter",
    # === Cloud & DevOps ===
    "aws", "amazon web services", "azure", "microsoft azure", "gcp",
    "google cloud", "google cloud platform", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "puppet", "chef", "jenkins", "ci/cd",
    "gitlab", "github actions", "circleci", "travis ci", "teamcity",
    "prometheus", "grafana", "elasticsearch", "kibana", "logstash",
    "elk stack", "datadog", "new relic", "splunk", "nagios", "zabbix",
    "helm", "vagrant", "packer", "consul", "vault", "istio",
    # === Databases ===
    "mysql", "postgresql", "postgres", "mongodb", "redis", "oracle",
    "oracle database", "sql server", "microsoft sql server", "mariadb",
    "sqlite", "cassandra", "apache cassandra", "dynamodb", "aws dynamodb",
    "firebase", "firestore", "snowflake", "bigquery", "redshift",
    "amazon redshift", "neo4j", "couchdb", "couchbase", "hbase",
    "influxdb", "timescaledb", "clickhouse", "supabase",
    # === Big Data & ETL ===
    "apache spark", "spark", "hadoop", "apache hadoop", "kafka",
    "apache kafka", "airflow", "apache airflow", "flink", "storm",
    "apache storm", "hive", "pig", "sqoop", "tableau", "power bi",
    "looker", "qlik", "qlikview", "qliksense", "dbt", "data bricks",
    "databricks", "snowflake", "etl", "data pipeline",
    # === Tools & IDEs ===
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "trello", "asana", "notion", "slack", "microsoft teams", "discord",
    "vs code", "visual studio code", "visual studio", "intellij",
    "intellij idea", "pycharm", "eclipse", "vim", "neovim", "emacs",
    "postman", "swagger", "openapi", "insomnia", "nginx", "apache",
    "apache http server", "iis", "docker compose", "linux", "unix",
    "windows server", "macos", "ubuntu", "centos", "red hat",
    # === Operating Systems ===
    "linux administration", "windows administration",
    "active directory", "ldap", "sso", "okta", "auth0",
    # === Data Science & ML ===
    "machine learning", "deep learning", "natural language processing",
    "nlp", "computer vision", "data science", "data analysis",
    "data engineering", "statistical analysis", "regression",
    "classification", "clustering", "neural networks", "llm",
    "large language models", "gen ai", "generative ai", "rag",
    "langchain", "llamaindex", "hugging face", "transformers",
    "predictive modeling", "time series", "a/b testing",
    # === Design ===
    "figma", "sketch", "adobe xd", "photoshop", "illustrator",
    "indesign", "after effects", "premiere pro", "lightroom",
    "ui/ux design", "user interface design", "user experience design",
    "user research", "usability testing", "prototyping", "wireframing",
    "responsive design", "mobile design", "design systems",
    "canva", "blender", "3ds max", "maya", "cinema 4d",
    "autocad", "solidworks", "catia", "revit",
    # === Project Management ===
    "project management", "program management", "product management",
    "agile", "scrum", "kanban", "safe", "lean", "waterfall",
    "jira administration", "confluence administration",
    "pmp", "pmi", "prince2", "itil", "csm", "cspo",
    # === Soft Skills ===
    "leadership", "team management", "team leadership",
    "stakeholder management", "client management", "vendor management",
    "strategic planning", "business strategy", "problem solving",
    "critical thinking", "communication", "negotiation",
    "conflict resolution", "decision making", "mentoring",
    "cross-functional collaboration", "public speaking",
    # === Architecture & Design Patterns ===
    "rest api", "restful api", "graphql api", "microservices",
    "service-oriented architecture", "soa", "event-driven architecture",
    "domain-driven design", "ddd", "clean architecture",
    "hexagonal architecture", "oauth", "jwt", "websocket",
    "grpc", "message queue", "rabbitmq", "celery", "redis",
    # === Security ===
    "cybersecurity", "information security", "network security",
    "penetration testing", "vulnerability assessment", "siem",
    "firewall", "ids/ips", "encryption", "iam",
    # === Emerging Tech ===
    "blockchain", "solidity", "web3", "smart contracts",
    "ethereum", "hyperledger", "iot", "internet of things",
    "arduino", "raspberry pi", "robotics", "automation",
    "rpa", "ui path", "automation anywhere", "blue prism",
    # === Enterprise Software ===
    "sap", "sap erp", "sap hana", "sap abap", "sap fiori",
    "salesforce", "salesforce admin", "salesforce development",
    "peoplesoft", "workday", "servicenow", "oracle erp",
    "oracle ebs", "microsoft dynamics", "dynamics 365",
    "hyperion", "cognos", "sas", "spss",
    # === Networking ===
    "ccna", "ccnp", "ccie", "cisco", "network administration",
    "tcp/ip", "dns", "dhcp", "vpn", "load balancing",
    "vmware", "vmware vsphere", "hyper-v", "citrix",
    # === Healthcare / Clinical ===
    "emr", "ehr", "epic", "cerner", "meditech", "hl7",
    "hipaa", "clinical research", "medical terminology",
    # === Finance & Accounting ===
    "quickbooks", "sage", "xero", "peachtree", "tally",
    "financial analysis", "financial modeling", "budgeting",
    "forecasting", "audit", "tax preparation", "bookkeeping",
    # === HR ===
    "recruiting", "talent acquisition", "onboarding", "payroll",
    "benefits administration", "employee relations", "hris",
    "performance management", "training and development",
    # === Marketing ===
    "seo", "sem", "ppc", "google ads", "facebook ads",
    "social media marketing", "content marketing", "email marketing",
    "marketing automation", "hubspot", "marketo", "salesforce marketing cloud",
    "google analytics", "adobe analytics", "mixpanel", "amplitude",
    "a/b testing", "conversion optimization", "crm",
    # === Sales ===
    "salesforce crm", "hubspot crm", "zoho crm", "pipedrive",
    "cold calling", "lead generation", "account management",
    "customer relationship management", "negotiation", "closing",
    # === Supply Chain & Logistics ===
    "supply chain management", "logistics", "inventory management",
    "warehouse management", "procurement", "sourcing",
    "erp", "mrp", "scm", "wms", "tms",
    # === Manufacturing ===
    "lean manufacturing", "six sigma", "kaizen", "5s",
    "root cause analysis", "fmea", "spc", "quality assurance",
    # === Construction ===
    "project estimation", "blueprint reading", "site management",
    "osha", "pmi", "primavera", "ms project",
    "autocad", "revit", "navisworks",
    # === Legal ===
    "legal research", "legal writing", "litigation", "contract law",
    "corporate law", "intellectual property", "compliance",
    "westlaw", "lexisnexis", "document review",
    # === Education ===
    "curriculum development", "lesson planning", "classroom management",
    "educational technology", "student assessment", "special education",
    "elearning", "instructional design", "moodle", "canvas",
    # === Design (Extended) ===
    "graphic design", "web design", "print design", "branding",
    "typography", "color theory", "layout design", "packaging design",
    # === Hospitality ===
    "hotel management", "restaurant management", "event planning",
    "catering", "housekeeping", "front desk", "concierge",
    "point of sale", "opentable", "micros",
    # === Aviation ===
    "aircraft maintenance", "flight operations", "aviation safety",
    "faa regulations", "dispatch", "crew scheduling",
    # === Agriculture ===
    "crop management", "livestock", "irrigation", "soil science",
    "agronomy", "farm management", "precision agriculture",
    # === Automotive ===
    "automotive repair", "diagnostics", "engine repair",
    "transmission", "electrical systems", "hvac",
    # === BPO ===
    "customer service", "call center", "bpo operations",
    "quality monitoring", "process optimization", "kpi management",
]

_SKILL_PATTERNS: list[tuple[str, re.Pattern]] = []
for skill in SKILLS_KEYWORDS:
    escaped = re.escape(skill)
    if len(skill.split()) > 1:
        pattern = re.compile(escaped, re.IGNORECASE)
    elif len(skill) <= 2:
        pattern = re.compile(rf"(?<![a-zA-Z]){escaped}(?![a-zA-Z])", re.IGNORECASE)
    else:
        pattern = re.compile(rf"(?<![a-zA-Z]){escaped}(?![a-zA-Z])", re.IGNORECASE)
    _SKILL_PATTERNS.append((skill, pattern))

_SECTION_BULLET_SPLIT = re.compile(r"[,;•·\|\n\r]+")

_SENTENCE_DETECT = re.compile(r"[.!?]$")


def extract_skills_dict(text: str) -> list[str]:
    found: set[str] = set()
    for skill, pattern in _SKILL_PATTERNS:
        if pattern.search(text):
            found.add(skill)
    return sorted(found, key=lambda s: -s.count(" "))


def extract_skills(text: str) -> list[str]:
    return extract_skills_dict(text)


def extract_skills_hybrid(text: str, skills_section_text: str | None = None) -> list[str]:
    return extract_skills_dict(text)
