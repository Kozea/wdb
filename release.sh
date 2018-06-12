#!/bin/bash
set -x
set -e
OLD_VERSION=$1
OLD_VERSION_RE=$(echo $OLD_VERSION | sed "s/\./\\\./g")
NEW_VERSION=$2
echo "$OLD_VERSION -> $NEW_VERSION"

git ls-files | grep -E ".+\.coffee|.+\.json|.+\.py" | xargs sed -i -e "s/$OLD_VERSION_RE/$NEW_VERSION/g"
pushd server
grunt
# python setup.py sdist bdist_wheel --universal --plat-name=linux-x86_64 upload
python setup.py sdist upload
popd

pushd client
# python setup.py sdist bdist_wheel --universal --plat-name=linux-x86_64 upload
python setup.py sdist upload
popd

sed -i "s/$OLD_VERSION/$NEW_VERSION/g" server/Dockerfile

git commit -am "Bump Version $OLD_VERSION -> $NEW_VERSION"
git tag $NEW_VERSION
git push
git push --tags
