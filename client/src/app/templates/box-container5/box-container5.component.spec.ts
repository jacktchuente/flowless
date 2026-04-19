import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BoxContainer5Component } from './box-container5.component';

describe('BoxContainer5Component', () => {
  let component: BoxContainer5Component;
  let fixture: ComponentFixture<BoxContainer5Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BoxContainer5Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BoxContainer5Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
