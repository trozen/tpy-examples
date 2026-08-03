# tplib is TurboPython's standard library: packages for
# common tasks, built for a statically compiled language.
import tplib.requests as requests
from tplib.json.model import model, field

@model  # inspired by pydantic
class Repo:
    full_name: str
    description: str
    language: str
    stars: int = field(alias="stargazers_count")
    forks: int = field(alias="forks_count")

def main() -> None:
    url = "https://api.github.com/repos/python/cpython"
    # inspired by requests, a popular Python package
    repo = Repo.from_json(requests.get(url).text)
    print(f"{repo.full_name} ({repo.language})")
    print(f"{repo.description}")
    print(f"{repo.stars} stars, {repo.forks} forks")

main()
