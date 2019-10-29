with import<nixpkgs> {};
let flask-markdown = pkgs.python3.pkgs.buildPythonPackage rec {
  pname = "Flask-Markdown";
  version = "0.3";

  propagatedBuildInputs = with python3Packages; [ flask markdown nose ];
  doCheck = false;
  src = pkgs.python3.pkgs.fetchPypi {
    inherit pname version;
    sha256 = "0l32ikv4f7va926jlq4f7gx0xid247bhlxl6bd9av5dk8ljz1hyq";
  };
}; in
stdenv.mkDerivation rec {
  name = "env";
  env = buildEnv { name = name; paths = buildInputs; };
  buildInputs = with pkgs; [ python3 flask-markdown ] ++ (with python3Packages; [ flask flask-bootstrap ]);
  shellHook = ''
    FLASK_DEBUG=1 FLASK_APP=main.py python -m flask run --host=0.0.0.0
    exit
  '';
}
