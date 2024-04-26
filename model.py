import torch
from torch.utils.data import DataLoader, random_split
from torch import nn, optim
from tqdm import tqdm
from dataset import MonteCarloDataset


class RNNWithErrorInjection(nn.Module):

    def __init__(self, input_size, hidden_size, output_size, context_size):
        super().__init__()
        self.hidden_size = hidden_size
        self.rnn = nn.RNN(input_size + 1 + context_size,
                          hidden_size,
                          batch_first=True)
        self.out = nn.Linear(hidden_size, output_size)

    def forward(self, input_seq, cumulative_outputs, context):
        batch_size = input_seq.size(0)
        seq_length = input_seq.size(1)

        hidden = self.init_hidden(batch_size)

        # Initialize errors tensor with zeros
        errors = torch.zeros(batch_size,
                             seq_length,
                             1,
                             device=input_seq.device)

        # Concatenate input sequence with zero error term and context for the first time step
        input_with_context_and_zero_error = torch.cat(
            (input_seq[:, :1],
             torch.zeros(batch_size, 1, 1,
                         device=input_seq.device), context.unsqueeze(1)),
            dim=-1)

        # Pass the input with zero error and context through the RNN for the first time step
        rnn_output, hidden = self.rnn(input_with_context_and_zero_error,
                                      hidden)
        predicted_cumulative_outputs = self.out(rnn_output)

        # Compute errors for time steps 1 to seq_length - 1
        errors[:, 1:] = cumulative_outputs[:, :-1].unsqueeze(
            -1) - predicted_cumulative_outputs

        # Concatenate input sequence with errors and context for time steps 1 to seq_length - 1
        input_with_errors_and_context = torch.cat(
            (input_seq[:, 1:], errors[:, 1:], context.unsqueeze(1).repeat(
                1, seq_length - 1, 1)),
            dim=-1)

        # Pass the input with errors and context through the RNN for time steps 1 to seq_length - 1
        outputs, _ = self.rnn(input_with_errors_and_context, hidden)
        outputs = torch.cat((predicted_cumulative_outputs, self.out(outputs)),
                            dim=1)

        # Invert normalization for the output
        outputs = outputs.squeeze(-1)
        return outputs, outputs[:, -1]

    def init_hidden(self, batch_size):
        return torch.zeros(1,
                           batch_size,
                           self.hidden_size,
                           device=next(self.parameters()).device)


def train(model, train_set, test_set, device, num_epochs):
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    losses = []

    try:
        for epoch in range(num_epochs):
            running_loss = 0.0

            # Training
            model.train()
            for _, (input_seq, cumulative_outputs,
                    context) in tqdm(enumerate(train_set),
                                     total=len(train_set)):
                input_seq = input_seq.to(device)
                cumulative_outputs = cumulative_outputs.to(device)
                context = context.to(device)

                optimizer.zero_grad()

                output, _ = model(input_seq, cumulative_outputs, context)
                loss = criterion(output, cumulative_outputs)

                loss.backward()
                optimizer.step()

                running_loss += loss.item()
            losses.append(running_loss / len(train_set))
            print(
                f"Epoch [{epoch+1}/{num_epochs}], Train Loss: {running_loss / len(train_set):.7f}"
            )

            # Validation
            print(f"Validation loss: {evaluate(model, test_set, device)}")
            if len(losses) > 1 and losses[-1] > losses[-2]:
                print("Stopping early due to lack of improvement!")
                break
    except KeyboardInterrupt:
        pass

    print("Training finished.")
    return losses


def evaluate(model, loader, device):
    val_loss = 0.0
    criterion = nn.MSELoss()
    model.eval()
    for _, (input_seq, cumulative_outputs, context) in enumerate(loader):
        input_seq = input_seq.to(device)
        cumulative_outputs = cumulative_outputs.to(device)
        context = context.to(device)
        output, _ = model(input_seq, cumulative_outputs, context)
        loss = criterion(output, cumulative_outputs)
        val_loss += loss.item()
    return val_loss


def get_loader(dataset):
    return DataLoader(dataset, batch_size=1024, num_workers=6, shuffle=True)


def train_with_default_params():
    # min values were precomputed to save time
    dataset = MonteCarloDataset('monte_carlo_tests',
                                'mc_out',
                                y_min=3.873e-7,
                                y_max=.009052538)
    #low, med, high = dataset.split_by_cache_size()
    med = dataset
    train_set, val_set = random_split(med, [.8, .2])
    train_set = get_loader(train_set)
    val_set = get_loader(val_set)
    model = RNNWithErrorInjection(2, 64, 1, 2)
    #model = load_model_default_params('trained_model.pth')
    device = torch.device('mps')
    model.to(device)
    losses = train(model, train_set, val_set, device, 10)
    torch.save(model.state_dict(), 'trained_model_alldata.pth')
    print(f"Loss history: {losses}")

    #print("Evaluating on low cache sizes...")
    #evaluate(model, low, device)
    #print("Evaluating on high cache sizes...")
    #evaluate(model, high, device)
    return model, losses
    #return model, []


def load_model_default_params(path: str):
    # Create an instance of the model with the same architecture
    model = RNNWithErrorInjection(2, 64, 1, 2)
    # Load the saved state dictionary
    model.load_state_dict(torch.load(path))
    # Set the model to evaluation mode
    model.eval()
    return model


if __name__ == '__main__':
    trained_model, loss_hist = train_with_default_params()
    print(loss_hist)
