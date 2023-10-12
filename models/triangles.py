from mesa import Agent, Model
from mesa.time import SimultaneousActivation


class Person(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self._totalSelf = 0
        self._nextTotalSelf = None

    def step(self):
        self.here(self.unique_id)
        if self._totalSelf > 0:
            for agent in self.model.scheduler.agents:
                pass

    def advance(self):
        self._totalSelf = self._nextTotalSelf
        self._nextTotalSelf = None


class TrianglesModel(Model):
    def __init__(self, N):
        self.num_agents = N
        self.scheduler = SimultaneousActivation(self)
        for i in range(self.num_agents):
            a = Person(i, self)
            self.scheduler.add(a)

    def step(self):
        self.scheduler.step()


if __name__ == '__main__':
    empty_model = TrianglesModel(10)
    empty_model.step()

