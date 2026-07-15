Third-Party Notices
===================

Enchan CLI uses and distributes components from several independent projects.
Third-party components remain subject to their own license terms. Enchan-specific
code, branding, and proprietary engine functionality are not relicensed by the
notices below.

llama.cpp / ggml
----------------
Source: https://github.com/ggml-org/llama.cpp
License: MIT
Usage: The platform runtime includes llama.cpp/ggml binaries built from the
upstream revision selected by the corresponding Enchan runtime release. Enchan
adds a minimal integration hook for its separately maintained engine; the
underlying model architecture and standard inference implementation remain
provided by llama.cpp/ggml.

The exact upstream revision for a packaged runtime is identified by its GitHub
Release tag and runtime version marker rather than by this notice.

MIT License

Copyright (c) 2023-2026 The ggml authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Web Awesome Free
----------------
Source: https://github.com/shoelace-style/webawesome
Version: 3.2.1
Usage: Locally bundled Select and Option Web Components for the Web UI
License: Web Awesome Free License

The complete license text is distributed with the Web UI at
`backend/webui/vendor/webawesome/LICENSE.md`.

Ollama compatibility/build components
-------------------------------------
Source: https://github.com/ollama/ollama
License: MIT
Usage: Ollama version metadata and compatibility/build changes are used to align
the packaged llama.cpp runtime. Ollama itself and its hosted service are not
presented as Enchan components.

MIT License

Copyright (c) Ollama

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Enchan Engine boundary
----------------------
The Enchan Engine library is maintained separately from llama.cpp, ggml, and
Ollama. It provides optional Enchan-specific processing through a narrow runtime
interface. References to third-party projects in this notice do not imply that
those projects sponsor, endorse, or license Enchan-specific functionality.

Models and separately installed packages
----------------------------------------
Model files are not part of the Enchan CLI source repository or the native
runtime package. Models obtained through Ollama or other providers remain subject
to the model provider's terms and notices.

Python packages listed in `requirements.txt` are installed separately from their
respective package indexes. They are not relicensed by Enchan CLI and remain
subject to the license metadata and terms supplied by their maintainers.
