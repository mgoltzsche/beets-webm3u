import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='beets-webm3u',
    version='0.2.0',
    author='Max Goltzsche',
    description='Serve M3U playlists via HTTP',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/mgoltzsche/beets-webm3u',
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'beets',
    ]
)
