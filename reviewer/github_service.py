import os
from github import Github
from github.GithubException import GithubException


SUPPORTED_EXTENSIONS = {
    ".py",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".java",
}

IGNORED_DIRECTORIES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
}


def detect_language_from_filename(filename):
    extension = os.path.splitext(filename)[1].lower()

    language_map = {
        ".py": "Python",
        ".cpp": "C++",
        ".cc": "C++",
        ".cxx": "C++",
        ".h": "C++",
        ".hpp": "C++",
        ".java": "Java",
    }

    return language_map.get(extension, "Unknown")


def should_include_file(path):
    normalized_path = path.replace("\\", "/")
    parts = normalized_path.split("/")

    if any(
        directory in IGNORED_DIRECTORIES
        for directory in parts
    ):
        return False

    extension = os.path.splitext(path)[1].lower()

    return extension in SUPPORTED_EXTENSIONS

def get_github_client():
    token = os.getenv("GITHUB_TOKEN")

    if token:
        return Github(token)

    return Github()

def get_repository_files(repository_url):
    github = get_github_client()

    repository_name = (
        repository_url
        .rstrip("/")
        .split("github.com/")[-1]
        .strip("/")
    )

    if not repository_name:
        raise ValueError(
            "Invalid GitHub repository URL."
        )

    try:
        repository = github.get_repo(repository_name)

        contents = repository.get_contents("")
        files = []

        while contents:
            current_item = contents.pop(0)

            if current_item.type == "dir":
                directory_name = current_item.path.split("/")[-1]

                if directory_name in IGNORED_DIRECTORIES:
                    continue

                contents.extend(
                    repository.get_contents(
                        current_item.path
                    )
                )

            elif current_item.type == "file":
                if not should_include_file(
                    current_item.path
                ):
                    continue

                try:
                    decoded_content = (
                        current_item.decoded_content
                        .decode("utf-8")
                    )
                except UnicodeDecodeError:
                    continue

                language = detect_language_from_filename(
                    current_item.name
                )

                files.append(
                    {
                        "name": current_item.name,
                        "path": current_item.path,
                        "language": language,
                        "content": decoded_content,
                    }
                )

        return {
            "success": True,
            "repository": repository.full_name,
            "files": files,
            "total_files": len(files),
        }

    except GithubException as error:
        return {
            "success": False,
            "repository": repository_name,
            "files": [],
            "total_files": 0,
            "error": str(error),
        }
    except Exception as error:
        return {
            "success": False,
            "repository": repository_name,
            "files": [],
            "total_files": 0,
            "error": str(error),
        }