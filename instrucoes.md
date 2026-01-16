Pra rodar o código é necessário:

Abrir o prompt de comando nessa pasta, com ctrl + shift + "

Ativar o ambiente virtual .venv com :

.venv\Scripts\activate

e depois rodar o código com
python manage.py runserver 0.0.0.0:8000

pra comunicar com os endpoints

depois que estiver rodando aqui pode ir para o front end e rodar o comando npm start --clear

Se der erros na ordem de serviço da eletro, o app que tem que ser ajustado é o OrdemdeServico

serializer - é o dto, que é a classe que transforma o objeto em json e vice versa
as views - são as classes que recebem as requisições e retornam as respostas
os services - são as classes que contêm a lógica de negócio

a ordemViewset - é a classe que contém as views para a ordem de serviço, o endpoint principal das ordens nele contem o crud todo

as urls - são as classes que contêm as urls para as views, nele contém a nomeação dos endpoints

se der algum pau nas ordens da mega guindastes só faz uma oração kkkkk
é o app de O_S
a arquitetura é a mesma
esta em REST, aí temos o serializer, as views, os services, a OsViewSet e as urls

Em pedidos é a agromusa que está usando o app de Pedidos
mesma coisa está em rest, teremos :
serializer - é o dto, que é a classe que transforma o objeto em json e vice versa
as views - são as classes que recebem as requisições e retornam as respostas
os services - são as classes que contêm a lógica de negócio
a PedidoVendaViewSet - é a classe que contém as views para o pedido, o endpoint principal dos pedidos nele contem o crud todo,
e também tem o endpoint de listar os pedidos por status
as urls - são as classes que contêm as urls para as views, nele contém a nomeação dos endpoints

