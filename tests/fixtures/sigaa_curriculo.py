"""
Trechos reais do SIGAA (consulta pública de graduação), capturados em 12/10/2026,
reduzidos ao mínimo necessário para os testes do extrator de currículos.

O texto e a estrutura das tags foram mantidos como no original. Cortes:
- linhas de tabela (cada constante indica o que ficou);
- scripts, cabeçalho e rodapé da página;
- a célula de ações (links "Visualizar Detalhes"/"Visualizar Programa") dos
  componentes, mantida apenas na primeira linha de cada relatório, pois o
  schema não usa os ids de componente.
"""

# Tela: GET /sigaa/public/curso/lista.jsf?nivel=G&aba=p-graduacao
# Reduzida de 158 para 4 cursos; o <caption> é o original.
# Colunas: [0] nome [1] grau [2] turno [3] sede [4] modalidade
#          [5] grau (repetido) [6] coordenação [7] lupa (href com id do curso)
# A unidade vem da linha de agrupamento td.subFormulario anterior ao curso.
HTML_LISTA_CURSOS = """
<table class="listagem" style="width: 90%;">
<caption>Cursos (158) </caption>
<thead>
<tr>
<th>Nome</th>
<th>Grau Acadêmico</th>
<th>Turno</th>
<th>Sede</th>
<th>Modalidade</th>
<th>Grau acadêmico</th>
<th>Coordenação</th>
<th></th>
</tr>
</thead>
<tbody>
<tr>
</tr>
<tr>
<td class="subFormulario" colspan="7">
										ADM - DEPTO ADMINISTRAÇÃO
										</td>
</tr>
<tr class="linhaPar">
<td>
							ADMINISTRAÇÃO
							</td>
<td>
									Bacharelado

								</td>
<td>
											NOTURNO

										</td>
<td>
								BRASÍLIA

								</td>
<td>Presencial</td>
<td>Bacharelado</td>
<td>OLINDA MARIA GOMES LESSES</td>
<td>
<a href="portal.jsf?id=414099&amp;lc=pt_BR&amp;nivel=G" title="Visualizar Página do Curso">
<img src="/sigaa/img/view.gif"/>
</a>
</td>
</tr>
<tr class="linhaImpar">
<td>
							ADMINISTRAÇÃO
							</td>
<td>
									Bacharelado

								</td>
<td>
											DIURNO

										</td>
<td>
								BRASÍLIA

								</td>
<td>Presencial</td>
<td>Bacharelado</td>
<td>CARLA PEIXOTO BORGES</td>
<td>
<a href="portal.jsf?id=414112&amp;lc=pt_BR&amp;nivel=G" title="Visualizar Página do Curso">
<img src="/sigaa/img/view.gif"/>
</a>
</td>
</tr>
<tr>
<td class="subFormulario" colspan="7">
										CIC - DEPTO CIÊNCIAS DA COMPUTAÇÃO
										</td>
</tr>
<tr class="linhaImpar">
<td>
							CIÊNCIA DA COMPUTAÇÃO
							</td>
<td>
									Bacharelado

								</td>
<td>
											DIURNO

										</td>
<td>
								BRASÍLIA

								</td>
<td>Presencial</td>
<td>Bacharelado</td>
<td>ROBERTA BARBOSA OLIVEIRA</td>
<td>
<a href="portal.jsf?id=414599&amp;lc=pt_BR&amp;nivel=G" title="Visualizar Página do Curso">
<img src="/sigaa/img/view.gif"/>
</a>
</td>
</tr>
<tr>
<td class="subFormulario" colspan="7">
										FCTE - CAMPUS UNB GAMA: FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM ENGENHARIA
										</td>
</tr>
<tr class="linhaImpar">
<td>
							ENGENHARIA DE SOFTWARE
							</td>
<td>
									Bacharelado

								</td>
<td>
											DIURNO

										</td>
<td>
								BRASÍLIA

								</td>
<td>Presencial</td>
<td>Bacharelado</td>
<td>JOHN LENON CARDOSO GARDENGHI</td>
<td>
<a href="portal.jsf?id=414924&amp;lc=pt_BR&amp;nivel=G" title="Visualizar Página do Curso">
<img src="/sigaa/img/view.gif"/>
</a>
</td>
</tr>
</tbody>
</table>
"""

# Tela: GET /sigaa/public/curso/portal.jsf?id=414924&lc=pt_BR&nivel=G
# Apenas o item "Ensino" do menu; o submenu só fica visível no hover.
HTML_PORTAL_CURSO = """
<li class="li-menu">
    <span class="item-menu" title="Ensino">Ensino</span>
    <div class="sub-menu">
        <ul>
            <li><a href="curriculo.jsf?lc=pt_BR&amp;id=414924">· Estruturas Curriculares</a></li>
            <li><a href="monografias.jsf?lc=pt_BR&amp;id=414924" "="">· Monografias</a></li>
            <li><a title="Turmas" href="turmas.jsf?lc=pt_BR&amp;id=414924">· Turmas</a></li>
        </ul>
    </div>
</li>
"""

# Tela: GET /sigaa/public/curso/curriculo.jsf?lc=pt_BR&id=414924 (ENGENHARIA DE SOFTWARE)
# Completa (3 estruturas). O primeiro tr.campos é o grupo de turno; o último é o total.
# Linha: [0] "Detalhes da Estrutura Curricular <código>, Criado em <ano>" [1] status
#        [2] links; o id interno da estrutura está no onclick ('id':'...').
HTML_ESTRUTURAS_CURSO = """
<form id="formCurriculosCurso" name="formCurriculosCurso" method="post" action="/sigaa/public/curso/curriculo.jsf" enctype="application/x-www-form-urlencoded">
<input type="hidden" name="formCurriculosCurso" value="formCurriculosCurso" />
<table id="table_lt" style="width: 100%">
<tbody>
<input type="hidden" name="nivel" value="G" />
<tr class="campos">
<td colspan="3">Matutino e Vespertino</td>
</tr>
<tr class="linha_par">
<td width="50%">
										Detalhes da Estrutura Curricular 6360/2,
										Criado em  2024
									</td>
<td width="45%">
										Ativa
									</td>
<td width="55px">
<a href="#" onclick="var a=function(){return prevenirDuploClique();};var b=function(){if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('formCurriculosCurso'),{'formCurriculosCurso:j_id_jsp_154341757_30':'formCurriculosCurso:j_id_jsp_154341757_30','id':'16220281'},'');}return false};return (a()==false) ? false : b();" title="Visualizar Estrutura Curricular"><img src="/sigaa/img/view.gif"/></a><a href="#" onclick="var a=function(){return prevenirDuploClique();};var b=function(){if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('formCurriculosCurso'),{'formCurriculosCurso:j_id_jsp_154341757_33':'formCurriculosCurso:j_id_jsp_154341757_33','id':'16220281'},'');}return false};return (a()==false) ? false : b();" title="Relatório da Estrutura Curricular"><img src="/sigaa/img/report.png"/></a>
</td>
</tr>
<tr class="linha_impar">
<td width="50%">
										Detalhes da Estrutura Curricular 6360/1,
										Criado em  2017
									</td>
<td width="45%">
										Inativa
									</td>
<td width="55px">
<a href="#" onclick="var a=function(){return prevenirDuploClique();};var b=function(){if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('formCurriculosCurso'),{'formCurriculosCurso:j_id_jsp_154341757_30j_id_1':'formCurriculosCurso:j_id_jsp_154341757_30j_id_1','id':'411'},'');}return false};return (a()==false) ? false : b();" title="Visualizar Estrutura Curricular"><img src="/sigaa/img/view.gif"/></a><a href="#" onclick="var a=function(){return prevenirDuploClique();};var b=function(){if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('formCurriculosCurso'),{'formCurriculosCurso:j_id_jsp_154341757_33j_id_1':'formCurriculosCurso:j_id_jsp_154341757_33j_id_1','id':'411'},'');}return false};return (a()==false) ? false : b();" title="Relatório da Estrutura Curricular"><img src="/sigaa/img/report.png"/></a>
</td>
</tr>
<tr class="linha_par">
<td width="50%">
										Detalhes da Estrutura Curricular 6360/-2,
										Criado em  2008
									</td>
<td width="45%">
										Inativa
									</td>
<td width="55px">
<a href="#" onclick="var a=function(){return prevenirDuploClique();};var b=function(){if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('formCurriculosCurso'),{'formCurriculosCurso:j_id_jsp_154341757_30j_id_2':'formCurriculosCurso:j_id_jsp_154341757_30j_id_2','id':'140'},'');}return false};return (a()==false) ? false : b();" title="Visualizar Estrutura Curricular"><img src="/sigaa/img/view.gif"/></a><a href="#" onclick="var a=function(){return prevenirDuploClique();};var b=function(){if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('formCurriculosCurso'),{'formCurriculosCurso:j_id_jsp_154341757_33j_id_2':'formCurriculosCurso:j_id_jsp_154341757_33j_id_2','id':'140'},'');}return false};return (a()==false) ? false : b();" title="Relatório da Estrutura Curricular"><img src="/sigaa/img/report.png"/></a>
</td>
</tr>
<!-- CURSO T&#201;CNICO -->
<!-- CURSO T&#201;CNICO INTEGRADO -->
<tr class="campos">
<td colspan="3">
<b>3
									Estruturas Curriculares Disponíveis
									</b>
</td>
</tr>
</tbody>
</table>
<input type="hidden" name="javax.faces.ViewState" id="javax.faces.ViewState" value="j_id2" />
</form>
"""

# Tela: POST /sigaa/public/curso/curriculo.jsf (Relatório da Estrutura Curricular 6360/2, ativa)
# Cabeçalho completo. Seções reduzidas: Optativas (2 de 72, incluindo nome com " - "),
# Complementares (vazia, original), 1º Nível (2 de 5) e 10º Nível (1 de 2).
HTML_RELATORIO_ATIVO = """
<form id="formulario" name="formulario" method="post" action="/sigaa/public/curso/relatorio_curriculo.jsf" enctype="application/x-www-form-urlencoded">
<input type="hidden" name="formulario" value="formulario">
		<h3 class="tituloTabela" style="width: 700px">Estrutura Curricular</h3>
		<table class="formulario" width="700px">
			<tbody><tr>
				<th>Código: </th>
				<td>6360/2</td>
			</tr>
				<tr>
					<th>Matriz Curricular: </th>
					<td>ENGENHARIA DE SOFTWARE/FCTE - Bacharelado - Presencial - D</td>
				</tr>
			<tr>
				<th>Período Letivo de Entrada em Vigor: </th>
				<td>2024.2</td>
			</tr>
			<tr>
				<th>Portaria/Ato Reconhecimento: </th>
				<td>Portaria SERES/MEC nº 313</td>
			</tr>
			<tr>
				<th>Data do Decreto: </th>
				<td>05/07/2024</td>
			</tr>
			<tr>
				<th>Data de Validade: </th>
				<td>
					INDEFINIDO
				</td>
			</tr>
			<tr>
				<td colspan="2" class="subFormulario">
				 	Prazos e Cargas Horárias
				</td>
			</tr>
			<tr>
				<th>Total Mínima: </th>
				<td>3525h</td>
			</tr>
			<tr>
				<td colspan="2" style="text-align: center; background-color: #EEEEEE">
					<b>Carga Horária Obrigatória</b>
				</td>
			</tr>
			<tr>
				<th>Subtotal de CH de Aula: </th>
				<td>
					2580h
				</td>
			</tr>
			<tr>
				<th>Subtotal de CH de Orientação Acadêmica/Profissional: </th>
				<td>
					405h
				</td>
			</tr>
			<tr style="border-bottom: 1px solid #DDDDDD;">
				<th>Total:</th>
				<td>
					2985h
				</td>
			</tr>
			<tr>
				<th width="48%">Carga Horária Optativa Mínima: </th>
				<td>540h</td>
			</tr><tr>
			</tr><tr>
				<th width="48%">Carga Horária Complementar Mínima: </th>
				<td>0h</td>
			</tr>
			<tr>
				<th>Carga Horária Obrigatória Atividade Acadêmica Específica: </th>
				<td>
					0h
				</td>
			</tr>
			<tr>
				<th>Carga Horária Máxima de Componentes Eletivos: </th>
				<td>360h</td>
			</tr>
			<tr>
				<th>Carga Horária Máxima por Período Letivo: </th>
				<td>480h</td>
			</tr>
			<tr style="border-bottom: 1px solid #DDDDDD;">
				<th>Carga Horária Mínima por Período Letivo: </th>
				<td>240h</td>
			</tr>
			<tr style="border-bottom: 1px solid #DDDDDD;">
				<th>Prazo Para Conclusão (em semestres): </th>
				<td>
			  		<table>
			  			<tbody><tr>
								<th>Mínimo: </th>
								<td>
									8 &nbsp;
								</td>
								<th>Médio: </th>
								<td>
									10  &nbsp;
								</td>
								<th>Máximo: </th>
								<td>
									16  &nbsp;
								</td>
			  			</tr>
					</tbody></table>
				</td>
			</tr>
				<tr>
					<td colspan="2">
						<table style="width: 100%">
							<tbody><tr class="tituloRelatorio">
								<td colspan="3">Optativas</td>
							</tr>
							<tr class="header">
								<td>Estrutura Curricular</td>
								<td>Natureza</td>
								<td>&nbsp;</td>
							</tr>
									<tr class="componentes">
										<td>CIC0191 - INTRODUÇÃO AO DESENVOLVIMENTO DE JOGOS - 60h</td>
										<td width="8%"><i>Optativa</i></td>
										<td width="8%" align="center">
<a href="#" title="Visualizar Detalhes do Componente Curricular" onclick="var a=function(){return prevenirDuploClique();};var b=function(){if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('formulario'),{'formulario:j_id_jsp_687993592_48':'formulario:j_id_jsp_687993592_48','id':'178535','publico':'public'},'');}return false};return (a()==false) ? false : b();"><img src="/sigaa/img/view.gif"></a><a href="#" title="Visualizar Programa" onclick="var a=function(){return prevenirDuploClique();};var b=function(){if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('formulario'),{'formulario:j_id_jsp_687993592_52':'formulario:j_id_jsp_687993592_52','idComponente':'178535'},'');}return false};return (a()==false) ? false : b();"><img src="/sigaa/img/report.png"></a>
										</td>
									</tr>
									<tr class="componentes">
										<td>LIP0174 - LÍNGUA DE SINAIS BRASILEIRA - BÁSICO - 60h</td>
										<td width="8%"><i>Optativa</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
							<tr>
								<td colspan="2"><b>CH Total:</b> 4275h. &nbsp;&nbsp;&nbsp; </td>
							</tr>
						</tbody></table>
						<table>
							<tbody><tr class="tituloRelatorio">
								<td colspan="3">Complementares</td>
							</tr>
							<tr class="header">
								<td>Estrutura Curricular</td>
								<td>Natureza</td>
								<td>&nbsp;</td>
							</tr>
								<tr>
									<td>Esta estrutura curricular não possui componentes complementares.</td>
									<td width="8%">&nbsp;</td>
									<td width="8%">&nbsp;</td>
								</tr>
							<tr>
								<td colspan="2"><b>CH Total:</b> 0h &nbsp;&nbsp;&nbsp; </td>
							</tr>
						</tbody></table>
						<table>
							<tbody><tr class="tituloRelatorio">
								<td colspan="3">1º Nível</td>
							</tr>
							<tr class="header">
								<td>Estrutura Curricular</td>
								<td>Natureza</td>
								<td>&nbsp;</td>
							</tr>
									<tr class="componentes">
										<td>CIC0004 - ALGORITMOS E PROGRAMAÇÃO DE COMPUTADORES - 90h</td>
										<td width="8%"><i>Obrigatória</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
									<tr class="componentes">
										<td>MAT0025 - CÁLCULO 1 - 90h</td>
										<td width="8%"><i>Obrigatória</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
							<tr>
								<td colspan="2"><b>CH Total:</b> 360h. &nbsp;&nbsp;&nbsp; </td>
							</tr>
							<tr class="tituloRelatorio">
								<td colspan="3">10º Nível</td>
							</tr>
							<tr class="header">
								<td>Estrutura Curricular</td>
								<td>Natureza</td>
								<td>&nbsp;</td>
							</tr>
									<tr class="componentes">
										<td>FGA0318 - ATIVIDADE DE EXTENSÃO ENGENHARIA DE SOFTWARE - 45h</td>
										<td width="8%"><i>Obrigatória</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
							<tr>
								<td colspan="2"><b>CH Total:</b> 135h. &nbsp;&nbsp;&nbsp; </td>
							</tr>
						</tbody></table>
					</td>
				</tr>
		</tbody><tfoot>
			<tr>
				<td colspan="2">&nbsp;</td>
			</tr>
		</tfoot>
		</table>
	<input type="hidden" name="javax.faces.ViewState" id="javax.faces.ViewState" value="j_id3">
</form>
"""

# Tela: POST /sigaa/public/curso/curriculo.jsf (Relatório da Estrutura Curricular 6360/-2, inativa)
# Casos de borda: versão negativa no código, optativa dentro de um Nível
# (CIC0004 no 1º Nível) e a seção "Grupos de Componentes Optativos", cujos
# componentes repetem os da seção Optativas e têm uma única célula, sem natureza.
# Cabeçalho completo. Seções reduzidas: Optativas (4 de 213), 1º Nível (2 de 4)
# e Grupos (1 de 5 cadeias). Complementares vazia, como no original.
HTML_RELATORIO_INATIVO = """
<form id="formulario" name="formulario" method="post" action="/sigaa/public/curso/relatorio_curriculo.jsf" enctype="application/x-www-form-urlencoded">
<input type="hidden" name="formulario" value="formulario">
		<h3 class="tituloTabela" style="width: 700px">Estrutura Curricular</h3>
		<table class="formulario" width="700px">
			<tbody><tr>
				<th>Código: </th>
				<td>6360/-2</td>
			</tr>
				<tr>
					<th>Matriz Curricular: </th>
					<td>ENGENHARIA DE SOFTWARE/FCTE - Bacharelado - Presencial - D</td>
				</tr>
			<tr>
				<th>Período Letivo de Entrada em Vigor: </th>
				<td>2008.2</td>
			</tr>
			<tr>
				<th>Portaria/Ato Reconhecimento: </th>
				<td>Portaria SERES/MEC nº 313</td>
			</tr>
			<tr>
				<th>Data do Decreto: </th>
				<td>05/07/2024</td>
			</tr>
			<tr>
				<th>Data de Validade: </th>
				<td>
					INDEFINIDO
				</td>
			</tr>
			<tr>
				<td colspan="2" class="subFormulario">
				 	Prazos e Cargas Horárias
				</td>
			</tr>
			<tr>
				<th>Total Mínima: </th>
				<td>3600h</td>
			</tr>
			<tr>
				<td colspan="2" style="text-align: center; background-color: #EEEEEE">
					<b>Carga Horária Obrigatória</b>
				</td>
			</tr>
			<tr>
				<th>Subtotal de CH de Aula: </th>
				<td>
					2130h
				</td>
			</tr>
			<tr>
				<th>Subtotal de CH de Orientação Acadêmica/Profissional: </th>
				<td>
					0h
				</td>
			</tr>
			<tr style="border-bottom: 1px solid #DDDDDD;">
				<th>Total:</th>
				<td>
					2130h
				</td>
			</tr>
			<tr>
				<th width="48%">Carga Horária Optativa Mínima: </th>
				<td>1470h</td>
			</tr><tr>
			</tr><tr>
				<th width="48%">Carga Horária Complementar Mínima: </th>
				<td>0h</td>
			</tr>
			<tr>
				<th>Carga Horária Obrigatória Atividade Acadêmica Específica: </th>
				<td>
					0h
				</td>
			</tr>
			<tr>
				<th>Carga Horária Máxima de Componentes Eletivos: </th>
				<td>360h</td>
			</tr>
			<tr>
				<th>Carga Horária Máxima por Período Letivo: </th>
				<td>480h</td>
			</tr>
			<tr style="border-bottom: 1px solid #DDDDDD;">
				<th>Carga Horária Mínima por Período Letivo: </th>
				<td>240h</td>
			</tr>
			<tr style="border-bottom: 1px solid #DDDDDD;">
				<th>Prazo Para Conclusão (em semestres): </th>
				<td>
			  		<table>
			  			<tbody><tr>
								<th>Mínimo: </th>
								<td>
									10 &nbsp;
								</td>
								<th>Médio: </th>
								<td>
									10  &nbsp;
								</td>
								<th>Máximo: </th>
								<td>
									16  &nbsp;
								</td>
			  			</tr>
					</tbody></table>
				</td>
			</tr>
				<tr>
					<td colspan="2">
						<table style="width: 100%">
							<tbody><tr class="tituloRelatorio">
								<td colspan="3">Optativas</td>
							</tr>
							<tr class="header">
								<td>Estrutura Curricular</td>
								<td>Natureza</td>
								<td>&nbsp;</td>
							</tr>
									<tr class="componentes">
										<td>CIC0004 - ALGORITMOS E PROGRAMAÇÃO DE COMPUTADORES - 90h</td>
										<td width="8%"><i>Optativa</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
									<tr class="componentes">
										<td>CIC0088 - COMPUTACAO BASICA - 90h</td>
										<td width="8%"><i>Optativa</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
									<tr class="componentes">
										<td>CIC0007 - INTRODUÇÃO À CIÊNCIA DA COMPUTAÇÃO - 60h</td>
										<td width="8%"><i>Optativa</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
									<tr class="componentes">
										<td>MAT0137 - CÁLCULO 1 - SEMIPRESENCIAL - 90h</td>
										<td width="8%"><i>Optativa</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
							<tr>
								<td colspan="2"><b>CH Total:</b> 16830h. &nbsp;&nbsp;&nbsp; </td>
							</tr>
						</tbody></table>
						<table>
							<tbody><tr class="tituloRelatorio">
								<td colspan="3">Complementares</td>
							</tr>
							<tr class="header">
								<td>Estrutura Curricular</td>
								<td>Natureza</td>
								<td>&nbsp;</td>
							</tr>
								<tr>
									<td>Esta estrutura curricular não possui componentes complementares.</td>
									<td width="8%">&nbsp;</td>
									<td width="8%">&nbsp;</td>
								</tr>
							<tr>
								<td colspan="2"><b>CH Total:</b> 0h &nbsp;&nbsp;&nbsp; </td>
							</tr>
						</tbody></table>
						<table>
							<tbody><tr class="tituloRelatorio">
								<td colspan="3">1º Nível</td>
							</tr>
							<tr class="header">
								<td>Estrutura Curricular</td>
								<td>Natureza</td>
								<td>&nbsp;</td>
							</tr>
									<tr class="componentes">
										<td>MAT0024 - CALCULO 1 - 90h</td>
										<td width="8%"><i>Obrigatória</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
									<tr class="componentes">
										<td>CIC0004 - ALGORITMOS E PROGRAMAÇÃO DE COMPUTADORES - 90h</td>
										<td width="8%"><i>Optativa</i></td>
										<td width="8%" align="center">
										</td>
									</tr>
							<tr>
								<td colspan="2"><b>CH Total:</b> 390h. &nbsp;&nbsp;&nbsp; </td>
							</tr>
						</tbody></table>
					</td>
				</tr>
				<tr>
					<td colspan="2">&nbsp;<br><br>
						<table width="100%">
						<tbody><tr class="tituloRelatorio"><td>Grupos de Componentes Optativos</td></tr>
						<tr class="header"><td>6360/-2 - CADEIA 2</td></tr>
						<tr class="componentes"><td>CIC0004 - ALGORITMOS E PROGRAMAÇÃO DE COMPUTADORES - 90h</td></tr>
						<tr class="componentes"><td>CIC0088 - COMPUTACAO BASICA - 90h</td></tr>
						<tr class="componentes"><td>CIC0007 - INTRODUÇÃO À CIÊNCIA DA COMPUTAÇÃO - 60h</td></tr>
						<tr>
							<td><b>CH Total:</b> 240h &nbsp;&nbsp;&nbsp; </td>
						</tr>
						<tr>
							<td><b>CH Mínima:</b> 60h &nbsp;&nbsp;&nbsp;<br>&nbsp; </td>
						</tr>
						</tbody></table>
					</td>
				</tr>
		</tbody><tfoot>
			<tr>
				<td colspan="2">&nbsp;</td>
			</tr>
		</tfoot>
		</table>
	<input type="hidden" name="javax.faces.ViewState" id="javax.faces.ViewState" value="j_id5">
</form>
"""
