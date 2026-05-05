-- Dados de teste para status e pedido
-- (Pre-requisito: ja ter rodado dados_cliente.sql)
USE bd_vendas;

-- Status possiveis para um pedido
INSERT INTO Status (idStatus, Descricao) VALUES
  (1, 'Aguardando Pagamento'),
  (2, 'Pago'),
  (3, 'Enviado'),
  (4, 'Entregue'),
  (5, 'Cancelado');

-- Pedidos (lembre: Cliente_idCliente referencia idCliente do INSERT anterior)
INSERT INTO Pedido
  (idPedido, Status_idStatus, DataPedido, ValorTotalPedido, Cliente_idCliente)
VALUES
  (1, 4, '2025-01-15', 150.00, 1),  -- Joao,    entregue
  (2, 2, '2025-02-10', 320.50, 1),  -- Joao,    pago
  (3, 3, '2025-02-20', 89.90,  2),  -- Maria,   enviado
  (4, 1, '2025-03-01', 1250.00, 5), -- Empresa X, aguardando
  (5, 4, '2025-03-15', 45.00,  3),  -- Carlos,  entregue
  (6, 5, '2025-03-20', 199.99, 6),  -- Pedro,   cancelado
  (7, 2, '2025-04-01', 720.00, 7);  -- Lucia,   pago
