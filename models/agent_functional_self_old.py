

class Model:

    def __init__(self):
        self.lastId = 0
    
    def register(self, agent):
        agent.id = self.lastId + 1
        self.lastId += 1
        self.agents[agent.id] = agent

    def deregister(self, agent):
        del self.agents[agent.id]
        agent.id = None


class Agent:
    """ Represents one person. """

    def __init__(self):
        """ Set up the initial state variables. """
        self.id = None

        # level of differentiation [0.0 - 100.0]
        self.differentiation = 0.25
        
        # Current anxiety [0.0 - 1.0]
        # Maybe "chronic anxiety" is a high level over time
        self.anxiety = 0.0

        # away / toward [-1.0 - 1.0]
        self.forces = {}

    def process(self, environment):
        """ This is the algorithm of the emotional system, called
        continuously to process pressure from the environment.
        Emotional shockwave would just be a bigger 'pressure' value.
        """

        # Just try to maintain an average of 0.0 toward and away?
        security = 0.0
        agents = self.forces.items()
        for id, force in agents:
            security += force

        # represents the person's internal equalibrium
        security /= len(agents)

        ## Now how to decide which people to get closer to?
        ## Is it always a move toward at the implicit sens of another?
        ## Should there be an attachment variable, like a priority?

        # Papero: A living sustem has to learn
        #   - Start with arbitrary values for priorities for ind/tog forces
        # Walter Elsasser: Reflections on a Theory of Organisms. Holism in Biology, (1998) Johns Hopkins University Press (JHU).
