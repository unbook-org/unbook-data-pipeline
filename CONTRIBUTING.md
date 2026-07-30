# Guia de Contribuição - UnBook 2.0 🚀

Obrigado por contribuir com o UnBook! Para manter a organização do código e o padrão profissional, siga as instruções abaixo.

## 🌿 Padrão de Branches

Nunca faça commits diretos na branch `main`. Crie branches a partir da `main` seguindo o padrão:

- `feat/nome-da-feature` — Para novas funcionalidades.
- `fix/descricao-do-bug` — Para correção de bugs.
- `docs/alteracao-doc` — Para mudanças em documentações.
- `chore/task-tecnica` — Para refatorações, atualizações de libs ou CI/CD.

## 📝 Padrão de Commits (Conventional Commits)

Utilizamos a convenção do [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: adiciona filtro por departamento no UnBoogle`
- `fix: corrige erro de autenticação via SSO`
- `docs: atualiza guia de instalação no README`
- `style: formatação de código de acordo com o linter`

## 🔀 Processo de Pull Request (PR)

1. Garanta que seu código está rodando sem erros e passando nos testes locais.
2. Abra um Pull Request apontando para a branch `develop`.
3. Preencha o template de PR detalhando o que foi feito.
4. Solicite o Code Review de pelo menos **1 membro do time/squad**.
5. Após a aprovação e o sucesso nos testes de CI, o merge poderá ser realizado.