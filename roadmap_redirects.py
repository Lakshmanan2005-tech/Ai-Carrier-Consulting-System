TOPIC_RESOURCES = {
    # Python
    "python basics": "https://docs.python.org/3/tutorial/index.html",
    "python variables": "https://docs.python.org/3/tutorial/introduction.html#using-python-as-a-calculator",
    "python data types": "https://docs.python.org/3/library/stdtypes.html",
    "python control flow": "https://docs.python.org/3/tutorial/controlflow.html",
    "python functions": "https://docs.python.org/3/tutorial/controlflow.html#defining-functions",
    "python oop": "https://docs.python.org/3/tutorial/classes.html",
    "python file handling": "https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files",
    "python generators": "https://wiki.python.org/moin/Generators",
    "python decorators": "https://wiki.python.org/moin/PythonDecorators",
    "python asyncio": "https://docs.python.org/3/library/asyncio.html",
    "flask": "https://flask.palletsprojects.com/",
    "django": "https://docs.djangoproject.com/",
    "fastapi": "https://fastapi.tiangolo.com/",

    # Java
    "java syntax": "https://docs.oracle.com/javase/tutorial/java/nutsandbolts/index.html",
    "java basics": "https://docs.oracle.com/javase/tutorial/java/nutsandbolts/index.html",
    "java collections": "https://docs.oracle.com/javase/tutorial/collections/index.html",
    "java multithreading": "https://docs.oracle.com/javase/tutorial/essential/concurrency/",
    "spring boot": "https://spring.io/projects/spring-boot",
    "hibernate": "https://hibernate.org/orm/documentation/",
    "maven": "https://maven.apache.org/guides/index.html",

    # Web Development
    "html5": "https://developer.mozilla.org/en-US/docs/Web/HTML",
    "css3": "https://developer.mozilla.org/en-US/docs/Web/CSS",
    "flexbox": "https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout",
    "grid": "https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout",
    "javascript": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Language_Overview",
    "react": "https://react.dev/learn",
    "vue": "https://vuejs.org/guide/introduction.html",
    "angular": "https://angular.io/docs",
    "dom manipulation": "https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Client-side_web_APIs/Manipulating_documents",

    # AI & ML
    "machine learning basics": "https://developers.google.com/machine-learning/crash-course",
    "neural networks": "https://pytorch.org/tutorials/beginner/blitz/neural_networks_tutorial.html",
    "deep learning": "https://www.deeplearning.ai/resources/",
    "natural language processing": "https://huggingface.co/learn/nlp-course/",
    "computer vision": "https://docs.opencv.org/master/d9/df8/tutorial_root.html",
    "pytorch": "https://pytorch.org/docs/stable/index.html",
    "tensorflow": "https://www.tensorflow.org/api_docs",

    # Cloud & DevOps
    "aws basics": "https://aws.amazon.com/getting-started/guides/",
    "docker": "https://docs.docker.com/get-started/",
    "kubernetes": "https://kubernetes.io/docs/home/",
    "terraform": "https://developer.hashicorp.com/terraform/intro",
    "jenkins": "https://www.jenkins.io/doc/",

    # C++
    "cpp syntax": "https://en.cppreference.com/w/cpp/language",
    "pointers": "https://en.cppreference.com/w/cpp/language/pointer",
    "stl": "https://en.cppreference.com/w/cpp/standard_library",
    "cmake": "https://cmake.org/documentation/",

    # Database
    "sql": "https://dev.mysql.com/doc/",
    "postgresql": "https://www.postgresql.org/docs/",
    "mongodb": "https://www.mongodb.com/docs/",
    "database basics": "https://www.sqlite.org/whentouse.html",

    # DevOps & Infrastructure
    "ci/cd": "https://about.gitlab.com/topics/ci-cd/",
    "ansible": "https://docs.ansible.com/",
    "prometheus": "https://prometheus.io/docs/introduction/overview/",

    # Testing
    "selenium": "https://www.selenium.dev/documentation/",
    "junit": "https://junit.org/junit5/docs/current/user-guide/",
    "pytest": "https://docs.pytest.org/en/stable/",

    # Mobile
    "kotlin": "https://kotlinlang.org/docs/home.html",
    "swift": "https://www.swift.org/documentation/",
    "flutter": "https://docs.flutter.dev/",

    # Others
    "git": "https://git-scm.com/doc",
    "github": "https://docs.github.com/en",
    "sqlite": "https://www.sqlite.org/docs.html",
    "rest api": "https://developer.mozilla.org/en-US/docs/Glossary/REST",
    "graphql": "https://graphql.org/learn/",
}

INTERVIEW_ANSWERS = {
    "list vs tuple": "https://docs.python.org/3/tutorial/datastructures.html#tuples-and-sequences",
    "global interpreter lock": "https://docs.python.org/3/glossary.html#term-global-interpreter-lock",
    "garbage collector": "https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/",
    "dom": "https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Introduction",
    "cia triad": "https://www.fortinet.com/resources/cyberglossary/cia-triad",
}

# No general search fallbacks allowed - strict documentation only.
