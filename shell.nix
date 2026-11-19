let
  nixpkgs = builtins.fetchTarball {
    # https://github.com/NixOS/nixpkgs/tree/release-25.05 latest commit
    url = "https://github.com/nixos/nixpkgs/archive/9ba04bda9249d5d5e5238303c9755de5a49a79c5.tar.gz";
    sha256 = "05im0w8g3hhqgimahllxrnqjzx21zmg6g7qfwq4w2862clgpihhz";
  };
  nixpkgs-unstable = builtins.fetchTarball {
    # https://github.com/NixOS/nixpkgs/tree/nixpkgs-unstable, for gh-actions-lock only
    url = "https://github.com/nixos/nixpkgs/archive/6dadaf4375be35033e1c84395adbd53ff5fded96.tar.gz";
    sha256 = "1g9sadx7zszll972hlv78675vc5vz2iw8v9jzs4338ccx8gzp48g";
  };
  pkgs = import nixpkgs { config = { allowUnfree = true; }; };
  inherit (import nixpkgs-unstable { }) gh-actions-lock;
in

pkgs.mkShell {
  name = "dev-shell";
  buildInputs = [
    pkgs.python311
    pkgs.poetry
    pkgs.codespell
    pkgs.pre-commit
    gh-actions-lock
  ];

  shellHook = ''
  # configure poetry to create virtualenv in ./.venv
  export POETRY_VENV_IN_PROJECT=1
  # poetry reports it needs this
  export LANG=en_US.UTF-8
  # support for building wheels:
  # https://nixos.org/nixpkgs/manual/#python-setup.py-bdist_wheel-cannot-create-.whl
  unset SOURCE_DATE_EPOCH
  '';
}
