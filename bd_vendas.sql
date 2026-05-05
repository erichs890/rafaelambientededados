-- Script DDL do banco bd_vendas (extraido do PDF do enunciado)
-- Para rodar: ver instrucoes no final do arquivo

-- -----------------------------------------------------
-- Schema BD_Vendas
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS BD_Vendas;
USE BD_Vendas;

-- -----------------------------------------------------
-- Table Categoria
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS Categoria (
  idCategoria INT NOT NULL,
  Descricao VARCHAR(45) NOT NULL,
  PRIMARY KEY (idCategoria)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table Produto
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS Produto (
  idProduto INT NOT NULL,
  Nome VARCHAR(45) NOT NULL,
  Descricao VARCHAR(200) NULL,
  Preco DECIMAL(18,2) NOT NULL DEFAULT 0,
  QuantEstoque DECIMAL(10,2) NOT NULL DEFAULT 0,
  Categoria_idCategoria INT NOT NULL,
  PRIMARY KEY (idProduto)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table TipoCliente
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS TipoCliente (
  idTipoCliente INT NOT NULL,
  Descricao VARCHAR(45) NULL,
  PRIMARY KEY (idTipoCliente)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table Cliente
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS Cliente (
  idCliente INT NOT NULL,
  Nome VARCHAR(45) NOT NULL,
  Email VARCHAR(100) NOT NULL,
  Nascimento DATETIME NULL,
  Senha VARCHAR(200) NULL,
  TipoCliente_idTipoCliente INT NOT NULL,
  DataRegistro DATETIME NOT NULL DEFAULT NOW(),
  PRIMARY KEY (idCliente)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table TipoEndereco
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS TipoEndereco (
  idTipoEndereco INT NOT NULL,
  Descricao VARCHAR(45) NOT NULL,
  PRIMARY KEY (idTipoEndereco)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table Endereco
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS Endereco (
  idEndereco INT NOT NULL,
  EnderecoPadrao TINYINT NOT NULL DEFAULT 0,
  Logradouro VARCHAR(45) NULL,
  Numero VARCHAR(45) NULL,
  Complemento VARCHAR(45) NULL,
  Bairro VARCHAR(45) NULL,
  Cidade VARCHAR(45) NULL,
  UF VARCHAR(2) NULL,
  CEP VARCHAR(8) NULL,
  TipoEndereco_idTipoEndereco INT NOT NULL,
  Cliente_idCliente INT NOT NULL,
  PRIMARY KEY (idEndereco)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table Telefone
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS Telefone (
  Numero VARCHAR(42) NOT NULL,
  Cliente_idCliente INT NOT NULL,
  PRIMARY KEY (Numero, Cliente_idCliente)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table Status
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS Status (
  idStatus INT NOT NULL,
  Descricao VARCHAR(45) NOT NULL,
  PRIMARY KEY (idStatus)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table Pedido
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS Pedido (
  idPedido INT NOT NULL,
  Status_idStatus INT NOT NULL,
  DataPedido DATETIME NOT NULL DEFAULT NOW(),
  ValorTotalPedido DECIMAL(18,2) NOT NULL DEFAULT 0,
  Cliente_idCliente INT NOT NULL,
  PRIMARY KEY (idPedido)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Table Pedido_has_Produto
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS Pedido_has_Produto (
  idPedidoProduto INT NOT NULL AUTO_INCREMENT,
  Pedido_idPedido INT NOT NULL,
  Produto_idProduto INT NOT NULL,
  Quantidade DECIMAL(10,2) NOT NULL,
  PrecoUnitario DECIMAL(18,2) NOT NULL,
  PRIMARY KEY (idPedidoProduto)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Foreign Keys
-- -----------------------------------------------------
CREATE INDEX fk_Produto_Categoria_idx ON Produto (Categoria_idCategoria ASC);
ALTER TABLE Produto
  ADD CONSTRAINT fk_Produto_Categoria
    FOREIGN KEY (Categoria_idCategoria)
    REFERENCES Categoria (idCategoria)
    ON DELETE NO ACTION ON UPDATE NO ACTION;

CREATE INDEX fk_Cliente_TipoCliente_idx ON Cliente (TipoCliente_idTipoCliente ASC);
ALTER TABLE Cliente
  ADD CONSTRAINT fk_Cliente_TipoCliente
    FOREIGN KEY (TipoCliente_idTipoCliente)
    REFERENCES TipoCliente (idTipoCliente)
    ON DELETE NO ACTION ON UPDATE NO ACTION;

CREATE INDEX fk_Endereco_TipoEndereco1_idx ON Endereco (TipoEndereco_idTipoEndereco ASC);
CREATE INDEX fk_Endereco_Cliente1_idx ON Endereco (Cliente_idCliente ASC);
ALTER TABLE Endereco
  ADD CONSTRAINT fk_Endereco_TipoEndereco
    FOREIGN KEY (TipoEndereco_idTipoEndereco)
    REFERENCES TipoEndereco (idTipoEndereco)
    ON DELETE NO ACTION ON UPDATE NO ACTION,
  ADD CONSTRAINT fk_Endereco_Cliente
    FOREIGN KEY (Cliente_idCliente)
    REFERENCES Cliente (idCliente)
    ON DELETE NO ACTION ON UPDATE NO ACTION;

CREATE INDEX fk_Telefone_Cliente_idx ON Telefone (Cliente_idCliente ASC);
ALTER TABLE Telefone
  ADD CONSTRAINT fk_Telefone_Cliente
    FOREIGN KEY (Cliente_idCliente)
    REFERENCES Cliente (idCliente)
    ON DELETE NO ACTION ON UPDATE NO ACTION;

CREATE INDEX fk_Pedido_Status1_idx ON Pedido (Status_idStatus ASC);
CREATE INDEX fk_Pedido_Cliente1_idx ON Pedido (Cliente_idCliente ASC);
ALTER TABLE Pedido
  ADD CONSTRAINT fk_Pedido_Status
    FOREIGN KEY (Status_idStatus)
    REFERENCES Status (idStatus)
    ON DELETE NO ACTION ON UPDATE NO ACTION,
  ADD CONSTRAINT fk_Pedido_Cliente
    FOREIGN KEY (Cliente_idCliente)
    REFERENCES Cliente (idCliente)
    ON DELETE NO ACTION ON UPDATE NO ACTION;

CREATE INDEX fk_Pedido_has_Produto_Produto_idx ON Pedido_has_Produto (Produto_idProduto ASC);
CREATE INDEX fk_Pedido_has_Produto_Pedido_idx ON Pedido_has_Produto (Pedido_idPedido ASC);
ALTER TABLE Pedido_has_Produto
  ADD CONSTRAINT fk_Pedido_has_Produto_Pedido
    FOREIGN KEY (Pedido_idPedido)
    REFERENCES Pedido (idPedido)
    ON DELETE NO ACTION ON UPDATE NO ACTION,
  ADD CONSTRAINT fk_Pedido_has_Produto_Produto
    FOREIGN KEY (Produto_idProduto)
    REFERENCES Produto (idProduto)
    ON DELETE NO ACTION ON UPDATE NO ACTION;

-- -----------------------------------------------------
-- Como rodar este script (tres opcoes):
-- -----------------------------------------------------
--
-- OPCAO 1 — MySQL Workbench (mais facil, com GUI):
--   1. Abra o MySQL Workbench
--   2. Conecte na sua instancia local (root / 132654)
--   3. File -> Open SQL Script -> selecione bd_vendas.sql
--   4. Clique no raio amarelo (Execute) ou aperte Ctrl+Shift+Enter
--
-- OPCAO 2 — Linha de comando (PowerShell no Windows):
--   No diretorio do projeto, rode:
--     & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p < bd_vendas.sql
--   Ele vai pedir a senha (132654).
--
-- OPCAO 3 — Cliente mysql interativo:
--   mysql -u root -p
--   (digita a senha)
--   mysql> source C:/Users/Erich/Downloads/estudo de cria/av2 Banco de dados/bd_vendas.sql
--
-- Depois confirme com:
--   USE bd_vendas;
--   SHOW TABLES;
-- Deve aparecer 10 tabelas.
