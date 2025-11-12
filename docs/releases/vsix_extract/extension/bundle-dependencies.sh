#!/bin/bash
# Bundle only essential dependencies

mkdir -p bundled_deps

# Copy only axios (essential for API calls)
if [ -d "node_modules/axios" ]; then
    cp -r node_modules/axios bundled_deps/
    cp -r node_modules/follow-redirects bundled_deps/
    cp -r node_modules/form-data bundled_deps/
    cp -r node_modules/proxy-from-env bundled_deps/
    echo "✅ Copied axios and its dependencies"
fi

# Create minimal node_modules structure
rm -rf node_modules
mv bundled_deps node_modules

echo "✅ Bundled essential dependencies"
ls -lh node_modules/
