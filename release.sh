#!/bin/bash -x
OLD_VERSION=$(echo $1 | sed "s/\./\\\./g")
NEW_VERSION=$2
echo "$OLD_VERSION -> $NEW_VERSION"

git ls-files | grep -E ".+\.coffee|.+\.json|.+\.py" | xargs sed -i -e "s/$OLD_VERSION/$NEW_VERSION/g"
pushd server
grunt
python setup.py sdist bdist_wheel upload
popd

pushd client
python setup.py sdist bdist_wheel upload
mv setup.py setup-full.py
mv setup-lite.py setup.py
python setup.py sdist bdist_wheel upload
mv setup.py setup-lite.py
mv setup-full.py setup.py
popd

git commit -am "Bump Version $OLD_VERSION -> $NEW_VERSION"
git tag $NEW_VERSION
git push --tags
