import argparse
import redis
import socket
import selectors
from utils import score
import hashlib

def conectar_Redis():          #Função de conectar ao Redis no localhost
    table = redis.Redis('localhost')
    return table

def obter_Hash():                                         #Função de pedir o Hash das cartas distribuídas
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('localhost', 5000))
    except:
        data = "I"
    else:
        s.send(f"HC".encode('utf-8'))
        data = s.recv(35).decode('utf-8')
    s.close()
    return data

def obter_Carta():                                         #Função para pedir uma carta ao servidor
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('localhost', 5000))
    except:
        data = "I"
    else:
        s.send(f"GC".encode('utf-8'))
        data = s.recv(2).decode('utf-8')
    s.close()
    return str(data).strip()

def jogo_Solitario():             #Função para jogo single player
    minhas_Cartas = []
    ultima_Carta = ""
    ronda_Inicial = True
    while True:
        if ronda_Inicial:                                                       #Ronda incial, vão ser pedidas 2 cartas ao deck
            c = obter_Carta()                                                   #Primeira carta
            if c == "I":                                                        #Sistema de prevenção de erros, caso não seja possível estabelecer ligação com o deck informar o jogador
                print(f"O deck não está atualmente disponível")
                exit(1)
            minhas_Cartas.append(c)
            c = obter_Carta()                                                   #Segunda carta
            if c == "I":                                                        #Sistema de prevenção de erros, caso não seja possível estabelecer ligação com o deck informar o jogador
                print(f"O deck não está atualmente disponível")
                exit(1)
            minhas_Cartas.append(c)    #Adicionar a carta à lista de cartas para depois ser calculado o score
            pontuacao = score(minhas_Cartas)    #Calcular pontuação
            ronda_Inicial = False    #Ronda inicial acabou, prosseguir com o jogo

        if ultima_Carta != "":       #Enquanto eu continuar a pedir cartas, adicionar ao meu deck e calcular a pontuação
            minhas_Cartas.append(ultima_Carta)
            pontuacao = score(minhas_Cartas)

        print(f"Pontuação Atual: {pontuacao}")    #Pontuação atual
        jogada = interact_with_user1(minhas_Cartas)  #Hash do deck, historial de jogadas

        if jogada == "H":           #Pedir uma carta
            ultima_Carta = obter_Carta()
        elif jogada == "S" :        #Passar a vez
            ultima_Carta = ""
        elif jogada == "W":         #Vitória
            print("Ganhou o jogo!")
            break
        elif jogada == "D":            #Derrota/"bust"
            print("Perdeu o jogo!")
            break
        
def aceitar_Conexao(sock, mask, numero):    #Função que vai aceitar a conexão e receber o número do jogador
    conn, addr = sock.accept()
    conn.setblocking(False)
    addr = conn.recv(128).decode('utf-8')       #Recebe
    conn.send(f"{numero}".encode('utf-8'))
    addr = str(addr).split(":")
    conn.close()
    return [str(addr[1]), int(addr[0])]

def receber_Mensagem(sock, mask):        #Função invocada pelo selector para receber mensagens de outros jogadores
    conn, addr = sock.accept() 
    conn.setblocking(False)
    data = ""
    while data == "":
        try:
            data = conn.recv(1).decode('utf-8')       #Recebe
        except:
            data = ""
    conn.close()
    return data

def informa_Jogadores(mensagem, conectados):      #Função que recebe uma mensagem e uma lista de numeros e portas estabelece conexão com cada porta para enviar a mensagem
    for n, port in conectados:
        if n == "Eu":
            continue
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', port))
        except:
            print(f"Erro ao conectar o jogador {n} à porta {port}")
        else:
            s.send(f"{mensagem}".encode('utf-8'))
        s.close()

def main(self_port, players_ports):              #Função principal, implementação do jogo ditribuído
    nao_conectados = list(args.players)          #Lista dos jogadores que ainda não estabeleceram conexão ao servidor
    conectados = []                              #Lista de jogadores que já se encontram concectados                                                                                   

    aJogar = list(nao_conectados)                #Jogadores que ainda estão em jogo, vão ser incluídos os que ainda não se conectaram pois ainda não tiveram hipótese de jogar
    aJogar.append(self_port)                     #Adicionar a minha porta
    aJogar = list(sorted(aJogar))                #Ordenar a lista dos jogadores que ainda estão em jogo

    numero = ""                                
    while numero == "":                          #Identificar o número do jogador
        numero = int(input("Jogador número:"))


    conexao = list(nao_conectados)                #Função de tentar conexão
    for i in range(len(nao_conectados)):
        conectados.append(['?', nao_conectados[i]])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', nao_conectados[i]))        #Conectar ao localhost com a porta dos não conectados
        except:
            s.close()                                          #Caso não se estabeleça ligação o programa fecha e avança, sendo que os jogadores não conectados pordem tentar estabelecer ligação mais tarde
        else:
            s.send(f"{self_port}:{numero}".encode('utf-8'))      #Envia o número da porta e o seu número para ligações futuras
            conectados[i][0] = s.recv(128).decode('utf-8')
            conexao.remove(nao_conectados[i])             #Após receber os jogadores conectados, remove os não conectados
            print(f"{conectados[i][0]} conectado à porta {conectados[i][1]}")     #Atribuição de porta ao jogador conectado
            s.close()
    nao_conectados = list(conexao)


    sock = socket.socket()                     #Criação de socket para receber ligações
    sock.bind(('localhost', self_port))
    sock.listen(100)
    sock.setblocking(False)

    selector = selectors.DefaultSelector()     #Criação do selector

    
    selector.register(sock, selectors.EVENT_READ, aceitar_Conexao)        #Programa entra em modo espera, até que ps outros jogadores estabelecem conexão


    #Função de esperar por todos os jogadores para se conectarem 

    while len(nao_conectados) != 0:      #Ciclo while que funciona desde que ainda haja jogadores não conectados
        print(f'À espera {len(nao_conectados)} jogadores para se conectarem à porta {nao_conectados}')
        events = selector.select()
        for key, mask in events:
            callback = key.data
            result = callback(key.fileobj, mask, numero)
            for i in range(len(conectados)):
                if conectados[i][1] == result[1]:
                    conectados[i] = result
                    break
            print(f"{result[0]} está conectado à porta {result[1]}")
            nao_conectados.remove(result[1])        #Vai-se remover da lista dos não conectados os jogadores acabados de conectar
    print("Todos os jogadores estão conectados e prontos a jogar")

    conectados.append(["Eu", self_port])      #Acrescentar a minha porta à lista de conectados

    conectados = sorted(conectados, key = lambda porta: porta[1])   #Ordenar a lista dos conectados pelo número da porta e de ordem crescente

    selector.unregister(sock)


    #seletor register connections
    selector.register(sock, selectors.EVENT_READ, receber_Mensagem)
    
    ronda_Inicial = True
    jogador_Atual = 0
    ultima_Carta = ""
    minhas_Cartas = []
    jogadas = [] 
    pontuacao = 0 

    while True:                                                #Para o decorrer do jogo vai ser usado um ciclo while True porque não se sabe ao certo quantas rondas é que o jogo vai ter 
        if len(aJogar) == 1:                                   #Caso só esteja 1 pessoa a jogar, terminar o jogo
            break
        if conectados[jogador_Atual][1] in aJogar:             #Passar à frente jogadores que já perderam
            if conectados[jogador_Atual][1] == self_port:      #Minha vez de jogar
                
                if ronda_Inicial:                              #Ronda Inicial, implementação semelhante à do singleplayer, vão ser pedidas 2 cartas iniciais
                    c = obter_Carta()                          #Obter a primeira carta
                    if c == "I":                               #Sistema de prevenção de erros, caso não seja disponível obter carta do deck, informar os outros jogadores que não foi possível obter a carta
                        print(f"O deck não está atualmente disponível")
                        informa_Jogadores("I", conectados)
                        selector.unregister(sock)
                        selector.close()
                        sock.close()
                        exit(1)                               
                    minhas_Cartas.append(c)                    #Adicionar a carta à lista das minhas cartas
                    c = obter_Carta()                          #Obter a segunda carta
                    if c == "I":                               #Sistema de prevenção de erros, caso não seja disponível obter carta do deck, informar os outros jogadores que não foi possível obter a carta
                        print(f"O deck não está atualmente disponível")
                        informa_Jogadores("I", conectados)
                        selector.unregister(sock)
                        selector.close()
                        sock.close()
                        exit(1)    
                    minhas_Cartas.append(c)                    #Adicionar a segunda carta à lista das minhas cartas
                    pontuacao = score(minhas_Cartas)           #Obter pontuação incial
                    ronda_Inicial = False                      #Acabou a ronda inicial, prosseguir com o jogo
                
                if ultima_Carta == 1:                          #Por cada carta pedida esta vai ser armazenada na variável ultima_Carta e só será adicionada à lista das cartas na próxima ronda
                    ultima_Carta = obter_Carta()
                    if c == "I":                               #Sistema de prevenção de erros, caso não seja disponível obter carta do deck, informar os outros jogadores que não foi possível obter a carta
                        print(f"O deck não está atualmente disponível")
                        informa_Jogadores("I", conectados)
                        selector.unregister(sock)
                        selector.close()
                        sock.close()
                        exit(1)

                if ultima_Carta != "":                         #Continua a adicionar a última carta pedida à lista das minhas cartas
                    minhas_Cartas.append(ultima_Carta)
                    pontuacao = score(minhas_Cartas)

                print(f"Pontuação atual: {pontuacao}")
                jogada = interact_with_user1(minhas_Cartas)    #Informa os outros jogadores das minhas cartas
                jogadas.append([jogador_Atual, jogada])
                
                if jogada == "H":                              #Pedir uma carta
                    ultima_Carta = 1
                    informa_Jogadores("H", conectados)                  #"H" == Hit/Pedir carta
                    print("À espera pelo resto dos jogadores fazerem a sua jogada")
                elif jogada == "S" :    
                    ultima_Carta = ""
                    informa_Jogadores("S", conectados)                  #"S" == Stand/Não pedir carta e passar a vez
                    print("À espera pelo resto dos jogadores fazerem a sua jogada")
                elif jogada == "W":        
                    informa_Jogadores("W", conectados)                  #"W" == Vitória, fim do jogo
                    print("Parabéns! Ganhou o jogo!")
                    break
                elif jogada == "D":          
                    informa_Jogadores("D", conectados)                  #"D" == Derrota, fim do jogo
                    aJogar.remove(self_port)                            #Como perdemos o jogo, remover a minha porta da lista de jogadores a jogar
                    print("Perdeu o jogo!")

            else:                                                          #Caso o programa identifique que não seja a sua vez de jogar fica a aguardar que o jogador informe a sua jogada
                while True:                                                #Aguardar pelas jogadas dos outros jogadores
                    events = selector.select()
                    for key, mask in events:
                        callback = key.data
                        jogada = callback(key.fileobj, mask)               #Recebe a jogada dos outros jogadores
                        break
                    break
                jogadas.append([jogador_Atual, jogada])
                if jogada == "H":                                                                           #"H" == Hit/Pedir carta
                    print(f"{conectados[jogador_Atual][0]} hit/pediu carta")
                elif jogada == "S":                                                                         #"S" == Stand/Não pedir carta e passar a vez
                    print(f"{conectados[jogador_Atual][0]} stand/passou a vez")
                elif jogada == "W":                                                                         #"W" == Vitória, fim do jogo
                    print(f"{conectados[jogador_Atual][0]} venceu o jogo")
                    break
                elif jogada == "D":                                                                         #"D" == Derrota, fim do jogo
                    print(f"{conectados[jogador_Atual][0]} perdeu e está fora do jogo")
                    aJogar.remove(conectados[jogador_Atual][1])                                            #Remover porta do jogador que perdeu
                else:
                    print("O deck não está atualmente disponível")
                    selector.unregister(sock)
                    selector.close()
                    sock.close()
                    exit(1)

        if jogador_Atual < len(conectados)-1:                            #Determinar o próximo a jogar
            jogador_Atual += 1
        else:
            jogador_Atual = 0     

    #Colocar as cartas na mesa através do Redis

    for n, port in conectados:
        if port == self_port:                                     #Caso o programa verifique que está na sua vez de colocar as cartas na mesa vai iniciar um cliente Redis e armazenar as cartas numa lista com a chave igual a self_port
            table = conectar_Redis()                              #Iniciar cliente Redis
            table.delete(str(self_port))
            for c in minhas_Cartas:
                table.rpush(str(self_port), str(c))
            informa_Jogadores("TB", conectados) 
        else:
            while True:                                            #Neste caso o programa vai aguardar até receber a confirmação do jogador a jogar
                events = selector.select()
                for key, mask in events:
                    callback = key.data
                    jogada = callback(key.fileobj, mask)           #Recebe a mensagem de confirmação
                    break
                break

    pontuacao_Jogadores = []              #Lista que vai conter a pontuação e as cartas dos outros jogadores
    
    #Obter as cartas dos outros jogadores

    for numero, port in conectados:
        if port == self_port:                                           #Caso a porta seja a minha porta, armazenar a minha porta, pontuação e as minhas cartas na lista
            pontuacao_Jogadores.append([port, pontuacao, minhas_Cartas])
        else:
            cards = table.lrange(str(port), 0, -1)              
            for i in range(len(cards)):
                cards[i] = cards[i].decode("utf-8")                     #O programa vai procurar no Redis a lista de cartas de cada jogador 
            pontuacao_Jogadores.append([port, score(cards), cards])     #Armazenar na lista a porta, pontuação e lista de cartas do jogador
    
    table.close()     #Fechar ligação com o Redis

    #Determinar o vencedor

    vencedor = 0          #Inicialiar a variável
    for port, pontuacao_final, cards in pontuacao_Jogadores:            #Consultar a lista para ver quem tem mais pontos    
        if pontuacao_final == 21:                                       #Caso a pontuação seja igual a 21 ganha automaticamente o jogo
            vencedor = port                                             #Obter a porta do vencedor
            break
        elif (21 > pontuacao_final) and (pontuacao_final > vencedor):   #Caso o jogador não tenha 21 pontos mas tenha mais pontos que o jogador anterior é considerado o vencero
            vencedor = port
        elif (pontuacao_final > 21):
            break

    for numero, port in conectados:                                     #Obter o número do vencedor
        if port == vencedor:
            vencedor = numero
            break
    print(f"O jogador número {vencedor} é o vencedor\033[m")
    exit

    #Hash md5 

    if (self_port == conectados[-2][1]) or (self_port == conectados[-1][1]):       #Quem vai pedir e verificar o hash das cartas vão ser os dois jogadores com maior porta
        hash_deck = obter_Hash()                                                   #Pedir o hash do deck
        cartas_Jogadas = []                                                        #Lista de cartas jogadas                                                       #Próxima jogada
        ronda_Inicial = True   
        proxima_Jogada = []  

        for i in range(len(conectados)):
            proxima_Jogada.append(0)
        for jogador, j in jogadas:                                                 #Vamos percorrer a lista jogadas visto conter todas as jogadas de cada jogador
            if ronda_Inicial:                                                      #Na ronda inicial vai-se pedir 2 cartas inciais
                cartas_Jogadas.append(pontuacao_Jogadores[jogador][2].pop(0)) 
                cartas_Jogadas.append(pontuacao_Jogadores[jogador][2].pop(0))
            if proxima_Jogada[jogador] == 1:
                cartas_Jogadas.append(pontuacao_Jogadores[jogador][2].pop(0))
            if (j == "H") and len(pontuacao_Jogadores[jogador][2]) != 0:                     
                proxima_Jogada[jogador] = 1
            if (jogador == len(pontuacao_Jogadores)-1) and ronda_Inicial:
                ronda_Inicial = False

        #Calcular o hash

        print(cartas_Jogadas)
        hash_jogado = hashlib.md5(f'{cartas_Jogadas}'.encode('utf-8')).hexdigest()
        print(hash_jogado)
        print(hash_deck)
        if str(hash_deck).strip() == str(hash_jogado).strip():                   #Comparar o hash das cartas jogadas com o hash do deck
            informa_Jogadores("TB", conectados[0:-2])               #Caso seja igual não houve batota e informamos os restantes jogadores que não houve batota                
        else:
            informa_Jogadores("B", conectados[0:-2])                #Caso seja diferente houve batota e informamos os restantes jogadores que houve batota

    else:                                                                        #Os restantes jogadores, com porta menor e que não foram escolhidos para comparar os hash vão ficar à espera de ser informado se houve batota ou não
        while True:
            events = selector.select()
            for key, mask in events:
                callback = key.data
                hash_jogado1 = callback(key.fileobj, mask)                       #Recebe a mensagem
                break
            break

        while True:
            events = selector.select()
            for key, mask in events:
                callback = key.data
                hash_jogado2 = callback(key.fileobj, mask)                     #Recebe a mensagem
                break
            break

    #Validação

    if (self_port == conectados[-2][1]) or (self_port == conectados[-1][1]):   #Portas dos jogadores com maior porta
        if str(hash_deck).strip() == str(hash_jogado).strip():
            print('Não houve batota')
        else:
            print("Houve batota!")

    else:
        if hash_jogado1 == "TB" and hash_jogado2 == "TB":       #Neste caso, a validação vai ser feita através da comparação das mensagens enviadas pelos jogadores que verificaram o hash, caso as duas mensagens sejam "Tudo bem" então não houve batota
            print('Não houve batota')
        else:
            print('Houve batota!')
    #close
    selector.unregister(sock)
    selector.close()
    sock.close()
    

def interact_with_user1(cards):
    """ All interaction with user must be done through this method.
    YOU CANNOT CHANGE THIS METHOD. """

    print(f"Current cards: {cards}")
    print("(H)it")
    print("(S)tand")
    print("(W)in")  # Claim victory
    print("(D)efeat") # Fold in defeat
    key = " "
    while key not in "HSWD":
        key = input("> ").upper()
    return key.upper() 


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--self', required=True, type=int)
    parser.add_argument('-p', '--players', nargs='+', type=int)      #eliminou-se o required para não ser obrigatório jogar com, no mínimo, 2 pessoas
    args = parser.parse_args()

    if not args.players:       #caso não haja argumentos "-p" executar o single player
        jogo_Solitario()
        exit()

    if args.self in args.players:
        print(f"{args.self} must not be part of the list of players")
        exit(1) 


    main(args.self, args.players)
