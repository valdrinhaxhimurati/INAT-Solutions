import os
import platform
import shutil
from pathlib import Path
from invoke import task


own_dir = Path(__file__).parent.resolve()


"""
Utility tasks
"""


@task
def distclean(c):
    """Completely clean dist folder"""
    os.chdir(own_dir.parent)
    for root, dirs, files in os.walk('./dist'):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


@task
def localinstall(c):
    """Install turandot in the local venv"""
    os.chdir(own_dir.parent)
    c.run("pip3 install .")


"""
PyPi tasks
"""


@task
def distbuild(c):
    """Build sdist and wheel to upload to PyPi"""
    os.chdir(own_dir.parent)
    c.run("python3 setup.py sdist bdist_wheel")


@task(pre=[distclean, distbuild])
def testpublish(c):
    """Publish package to temporary PyPi"""
    os.chdir(own_dir.parent)
    c.run("twine upload --repository testpypi dist/*")


@task(pre=[distclean, distbuild])
def publish(c):
    """Publish package to PyPi"""
    os.chdir(own_dir.parent)
    c.run("twine upload dist/*")

